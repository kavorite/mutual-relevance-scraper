# mutual-relevance-scraper

----

Simple PRAW script for scraping concatenated posts, both relevant and irrelevant
to one another, depth-first from random Reddit comment pools. To use, first set
the environment variables `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`, then
run like so:
```
$ python data.py
```

- `data.py` — print supervised fastText annotations to stdout

TODO: measure toxicity v. supportiveness: Some replies are constructive, and
some aren't; we should be able to measure either a lack of attacks or presence
of positive features in responses, though fastText may not represent the most
accurate means to accomplish this 
