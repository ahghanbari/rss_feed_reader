from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from feeds.models import Source, Post
import feedparser as parser

import time
import datetime
import requests
import pyrfc3339
import json
import hashlib


class NullOutput(object):
    ''' little class for when we have no outputter ''' 
    def write(self, str):
        pass


def _customize_sanitizer(fp):
    bad_attributes = ["align", "valign", "hspace", "class", "width", "height"]

    for item in bad_attributes:
        try:
            if item in fp._HTMLSanitizer.acceptable_attributes:
                fp._HTMLSanitizer.acceptable_attributes.remove(item)
        except Exception:
            pass


def get_agent(source_feed):
    return "{user_agent} (+{server}; Updater;)".format(
        user_agent=settings.FEEDS_USER_AGENT, server=settings.FEEDS_SERVER
    )

def update_feeds(max_feeds=10, user=None, output=NullOutput()):

    if user:
        todo = Source.objects.filter(Q(live = True) & Q(user=user) & Q(next_poll__lt = timezone.now()))
    else:
        todo = Source.objects.filter(Q(live = True) & Q(next_poll__lt = timezone.now()))

    output.write("Queue size is {}".format(todo.count()))
    sources = todo[:max_feeds]
    output.write("\nProcessing %d\n\n" % sources.count())
    for src in sources:
        read_feed(src, output)  


def read_feed(source_feed, output=NullOutput()):

    output.write("\n------------------------------\n")
    agent = get_agent(source_feed)
    headers = {"User-Agent": agent}
    feed_url = source_feed.feed_url
    output.write("\nFetching %s" % feed_url)

    ret = None
    try:
        ret = requests.get(
            feed_url, headers=headers, verify=False, allow_redirects=False, timeout=20
        )
        output.write(str(ret))
    except Exception as ex:
        source_feed.last_result = False
        source_feed.num_of_failed_polls += 1
        if source_feed.num_of_failed_polls > settings.FEEDS_MAX_FAILED_POLLS:
            source_feed.live = False
        source_feed.next_poll = timezone.now() + datetime.timedelta(0, settings.FEEDS_DELAY_BEFORE_NEXT_POLL)
        source_feed.save(update_fields=["last_result", "num_of_failed_polls", "live", "next_poll"])
        output.write("\nFetch error: " + str(ex))
        return
    
    if ret and ret.status_code >= 200 and ret.status_code < 300:
        content_type = "Not Set"
        if "Content-Type" in ret.headers:
            content_type = ret.headers["Content-Type"]

        (ok, changed) = import_feed(
            source_feed=source_feed,
            feed_body=ret.content,
            content_type=content_type,
            output=output,
        )
    if not ok:
        source_feed.last_result = False
        source_feed.num_of_failed_polls += 1
        if source_feed.num_of_failed_polls > settings.FEEDS_MAX_FAILED_POLLS:
            source_feed.live = False
        source_feed.next_poll = timezone.now() + datetime.timedelta(0, settings.FEEDS_DELAY_BEFORE_NEXT_POLL)
        source_feed.save(update_fields=["last_result", "num_of_failed_polls", "live", "next_poll"])

def import_feed(source_feed, feed_body, content_type, output=NullOutput()):
    ok = False
    changed = False

    if "xml" in content_type or feed_body[0:1] == b"<":
        (ok, changed) = parse_feed_xml(source_feed, feed_body, output)
    elif "json" in content_type or feed_body[0:1] == b"{":
        (ok, changed) = parse_feed_json(source_feed, str(feed_body, "utf-8"), output)
    else:
        ok = False
    return (ok, changed)


def parse_feed_xml(source_feed, feed_content, output):

    ok = True
    changed = False
    try:
        _customize_sanitizer(parser)
        f = parser.parse(feed_content)
        entries = f["entries"]
        if not len(entries):
            ok = False

    except Exception as ex:
        entries = []
        ok = False

    if ok:
        try:
            source_feed.name = f.feed.title
            source_feed.save(update_fields=["name"])
        except Exception as ex:
            output.write("\nUpdate name error:" + str(ex))
            pass

        try:
            source_feed.image_url = f.feed.image.href
            source_feed.save(update_fields=["image_url"])
        except:
            pass

        # either of these is fine, prefer description over summary
        # also feedparser will give us itunes:summary etc if there
        try:
            source_feed.description = f.feed.summary
        except:
            pass

        try:
            source_feed.description = f.feed.description
        except:
            pass

        try:
            source_feed.save(update_fields=["description"])
        except:
            pass

        # output.write(entries)
        entries.reverse()  # Entries are typically in reverse chronological order - put them in right order
        for e in entries:
            # we are going to take the longest
            body = ""
            if hasattr(e, "content"):
                for c in e.content:
                    if len(c.value) > len(body):
                        body = c.value

            if hasattr(e, "summary"):
                if len(e.summary) > len(body):
                    body = e.summary

            if hasattr(e, "summary_detail"):
                if len(e.summary_detail.value) > len(body):
                    body = e.summary_detail.value

            if hasattr(e, "description"):
                if len(e.description) > len(body):
                    body = e.description

            try:
                guid = e.guid
            except Exception as ex:
                try:
                    guid = e.link
                except Exception as ex:
                    m = hashlib.md5()
                    m.update(body.encode("utf-8"))
                    guid = m.hexdigest()

            try:
                p = Post.objects.filter(source=source_feed).filter(guid=guid)[0]
                output.write("EXISTING " + guid + "\n")

            except Exception as ex:
                output.write("NEW " + guid + "\n")
                p = Post(index=0, body=" ", title="", guid=guid)
                p.found = timezone.now()
                changed = True

                try:
                    p.created = datetime.datetime.fromtimestamp(
                        time.mktime(e.published_parsed)
                    ).replace(tzinfo=timezone.utc)

                except Exception as ex2:
                    output.write("CREATED ERROR:" + str(ex2))
                    p.created = timezone.now()

                p.source = source_feed
                p.save()

            try:
                p.title = e.title
                p.save(update_fields=["title"])
            except Exception as ex:
                output.write("Title error:" + str(ex))

            try:
                p.link = e.link
                p.save(update_fields=["link"])
            except Exception as ex:
                output.write("Link error:" + str(ex))

            try:
                p.image_url = e.image.href
                p.save(update_fields=["image_url"])
            except:
                pass

            try:
                p.author = e.author
                p.save(update_fields=["author"])
            except Exception as ex:
                p.author = ""

            try:
                p.body = body
                p.save(update_fields=["body"])
            except Exception as ex:
                output.write(str(ex))
                output.write(p.body)
    return (ok, changed)


def parse_feed_json(source_feed, feed_content, output):

    ok = True
    changed = False

    try:
        f = json.loads(feed_content)
        entries = f["items"]
        if not len(entries):
            ok = False

    except Exception as ex:
        ok = False

    if ok:
        if "expired" in f and f["expired"]:
            return (False, False, source_feed.interval)

        try:
            source_feed.name = f["title"]
            source_feed.save(update_fields=["title"])
        except Exception as ex:
            pass

        try:
            if "description" in f:
                _customize_sanitizer(parser)
                source_feed.description = parser._sanitizeHTML(
                    f["description"], "utf-8", "text/html"
                )
                source_feed.save(update_fields=["description"])
        except Exception as ex:
            pass

        try:
            _customize_sanitizer(parser)
            source_feed.name = parser._sanitizeHTML(
                source_feed.name, "utf-8", "text/html"
            )
            source_feed.save(update_fields=["name"])

        except Exception as ex:
            pass

        try:
            if "icon" in f:
                source_feed.image_url = f["icon"]
                source_feed.save(update_fields=["icon"])
        except Exception as ex:
            pass

        # output.write(entries)
        entries.reverse()  # Entries are typically in reverse chronological order - put them in right order
        for e in entries:
            body = " "
            if "content_text" in e:
                body = e["content_text"]
            if "content_html" in e:
                body = e["content_html"]  # prefer html over text

            try:
                guid = e["id"]
            except Exception as ex:
                try:
                    guid = e["url"]
                except Exception as ex:
                    m = hashlib.md5()
                    m.update(body.encode("utf-8"))
                    guid = m.hexdigest()

            try:
                p = Post.objects.filter(source=source_feed).filter(guid=guid)[0]
                output.write("EXISTING " + guid + "\n")

            except Exception as ex:
                output.write("NEW " + guid + "\n")
                p = Post(index=0, body=" ")
                p.found = timezone.now()
                changed = True
                p.source = source_feed

            try:
                title = e["title"]
            except Exception as ex:
                title = ""

            # borrow the RSS parser's sanitizer

            _customize_sanitizer(parser)
            body = parser._sanitizeHTML(
                body, "utf-8", "text/html"
            )  # TODO: validate charset ??
            _customize_sanitizer(parser)
            title = parser._sanitizeHTML(
                title, "utf-8", "text/html"
            )  # TODO: validate charset ??
            # no other fields are ever marked as |safe in the templates

            if "banner_image" in e:
                p.image_url = e["banner_image"]

            if "image" in e:
                p.image_url = e["image"]

            try:
                p.link = e["url"]
            except Exception as ex:
                p.link = ""

            p.title = title

            try:
                p.created = pyrfc3339.parse(e["date_published"])
            except Exception as ex:
                output.write("CREATED ERROR")
                p.created = timezone.now()

            p.guid = guid
            try:
                p.author = e["author"]
            except Exception as ex:
                p.author = ""

            p.save()

            try:
                seen_files = []
                for ee in list(p.enclosures.all()):
                    # check existing enclosure is still there
                    found_enclosure = False
                    if "attachments" in e:
                        for pe in e["attachments"]:

                            if pe["url"] == ee.href and ee.href not in seen_files:
                                found_enclosure = True

                                try:
                                    ee.length = int(pe["size_in_bytes"])
                                except:
                                    ee.length = 0

                                try:
                                    type = pe["mime_type"]
                                except:
                                    type = "audio/mpeg"  # we are assuming podcasts here but that's probably not safe

                                ee.type = type
                                ee.save()
                                break
                    if not found_enclosure:
                        ee.delete()
                    seen_files.append(ee.href)

                if "attachments" in e:
                    for pe in e["attachments"]:

                        try:
                            if pe["url"] not in seen_files:

                                try:
                                    length = int(pe["size_in_bytes"])
                                except:
                                    length = 0

                                try:
                                    type = pe["mime_type"]
                                except:
                                    type = "audio/mpeg"

                                ee = Enclosure(
                                    post=p, href=pe["url"], length=length, type=type
                                )
                                ee.save()
                        except Exception as ex:
                            pass
            except Exception as ex:
                if output:
                    output.write("No enclosures - " + str(ex))

            try:
                p.body = body
                p.save()
                # output.write(p.body)
            except Exception as ex:
                output.write(str(ex))
                output.write(p.body)

    return (ok, changed)


def test_feed(source, cache=False, output=NullOutput()):
    headers = {
        "User-Agent": get_agent(source)
    }  # identify ourselves and also stop our requests getting picked up by any cache

    if cache:
        if source.last_modified:
            headers["If-Modified-Since"] = str(source.last_modified)
    else:
        headers["Cache-Control"] = "no-cache,max-age=0"
        headers["Pragma"] = "no-cache"

    output.write("\n" + str(headers))

    ret = requests.get(
        source.feed_url,
        headers=headers,
        allow_redirects=False,
        verify=False,
        timeout=20,
    )

    output.write("\n\n")
    output.write(str(ret))
    output.write("\n\n")
    output.write(ret.text)