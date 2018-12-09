# mutual-relevance-scraper

Simple PRAW script for scraping concatenated posts, both relevant and irrelevant
to one another, depth-first from random Reddit comment pools. To use, first set
the environment variables `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`, then
run like so:
```
$ python data.py --length 0.1G --encoding utf-8 -o annotations.txt
```
**note:** *while it is possible to redirect `stdout`, using `--opath` allows*
*data.py to remember where it left off and account for progress accordingly.*

- `data.py` — print supervised fastText annotations to stdout

TODO: measure toxicity v. supportiveness: Some replies are constructive, and
some aren't; we should be able to measure either a lack of attacks or presence
of positive features in responses, though fastText may not represent the most
accurate means to accomplish this
