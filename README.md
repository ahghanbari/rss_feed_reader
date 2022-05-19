## RSS scraper

Best RSS reader u ever seen :)

for run (obviously u need docker and docker-compose):

```bash
sudo docker-compose up --build
```

for refreshing all feed manually:
```bash
python3 manage.py refreshfeeds
```

some curl example for graphql:
```bash
curl http://localhost:/graphql -H "Authorization: JWT $token" -d query="query { oneFeed(sourceId: $id) {title } }"

curl http://localhost:/graphql -H "Authorization: JWT $token" -d query="query allSources { allSources { name, id } }"

curl http://localhost:/graphql -H "Authorization: JWT $token" -d query='mutation addSource { addSource(input: { feedUrl: "https://rss.art19.com/apology-line"}) { ok } }'
```

some graphql example query:

```bash
mutation createUser {
  createUser(username: "<your_username>", password: "<your_password>", email: "<your_email>") {
    token
    user {
      username
    }
  }
}

mutation verifyToken {
  verifyToken(token: "<your_token>") {
    payload
  }
}

mutation refreshToken {
  refreshToken(refreshToken: "<refresh_token>") {
    token
  }
}

mutation loginUser {
  tokenAuth(username: "<username>", password: "<password>") {
    token
  }
}

mutation addSource {
  addSource(token: "<your_token>") {
    ok
  }
}

mutation remvoeSource {
  remvoeSource(feedUrl: "<feed_url>") {
    ok
  }
}

query allSources {
  allSources
  {
    name,
    id
  }
}
```
