import praw
import random
import itertools as it
from os import environ as env
import unicodedata as ud
from collections import deque

r = praw.Reddit(client_id=env["REDDIT_CLIENT_ID"],
                client_secret=env["REDDIT_CLIENT_SECRET"],
                user_agent='mutual-relevance-scraper')

PARTITION = '||'

def sanitize(s: str):
    s = ''.join(c if ud.category(c)[0] != 'P' else f' {c} ' for c in s)
    return ' '.join(t for t in s.strip().split() if t != PARTITION)

def randomSubmission():
    return r.subreddit('all').random()

def depthPairs(submission, breadthFirst=True):
    submission.comments.replace_more(limit=None)
    cq = deque(zip(it.repeat(1), submission.comments[:]))

    while cq:
        comment, depth = cq.popleft()
        enqueue = cq.extend if breadthFirst else cq.extendLeft
        enqueue(zip(it.repeat(depth+1), comment.replies))
        yield (comment, depth)

def positiveSamples(submission):
    previous = None
    for tail, d_tail in depthPairs(submission, False):
        if previous is None:
            previous = comment, depth
            continue
        head, d_head = previous
        if d_tail > d_head:
            yield (head, tail)

# return a random comment and its depth
def randomComment():
    submission = randomSubmission()
    return random.choice(replyPairs(submission, False))

# negative sampling — build tuples of unrelated comments
def negativeSample():
    head, d_head = randomComment()
    tail, d_tail = randomComment()
    if d_head < d_tail:
        # swap 'em
        head, tail = tail, head
    return head, tail

def samples(negativeSkew = 0.5, n=float('inf')):
    negatives = 0
    total = 0
    pq = deque()
    while total < n:
        if len(pq) == 0:
            pq.append(positiveSamples(randomSubmission()))
        negative = negatives < negativeSkew * total
        total += 1
        if negative: negative += 1
        sample = negativeSample() if negative else pq.popleft()
        yield (negative, sample)

def annotations(n=10000):
    for negative, pair in samples():
        head, tail = pair
        call = sanitize(head.body)
        response = sanitize(tail.body)
        label = 'negative' if negative else 'positive'
        yield f'__label__{label} {call} {PARTITION} {response}'

if __name__ == '__main__':
    from sys import argv, stdout
    if len(argv) > 1:
        data = annotations(int(argv[1]))
    else:
        data = annotations()

    data = (f'{ln}\r\n' for ln in data)
    try:
        for ln in data:
            stdout.write(ln)
    except KeyboardInterrupt:
        pass
