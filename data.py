import praw
import random
import regex as re
import itertools as it
from os import environ as env
import unicodedata as ud
from collections import deque

r = praw.Reddit(client_id=env["REDDIT_CLIENT_ID"],
                client_secret=env["REDDIT_CLIENT_SECRET"],
                user_agent='mutual-relevance-scraper')

PARTITION = '||'

URI_RGX = re.compile("(\w+:/)?[/a-zA-Z0-9.]+")
PUNCT_RGX = re.compile('\p{P}')

def sanitize(s: str):
#    TODO: Better URI tokenization
#    PUNCT_RGX.sub(s, ' \\1 ')
#    def tokens():
#        for t in s.split():
#            if URI_RGX.match(s):
#                yield s
#            else:
#                cq = ''
#                for c in s:
#                    if ud.category(c)[0] == 'P':
#                        yield cq
#                        yield c
#                    cq += c
#
#        splitp = lambda c: ud.category(c) == 'P' && c
#        for t in s.split():
#            t = list(t)
#            if ud.category(t[0])[0] == 'P':
#                yield t.pop(0)
#            if ud.category(t[-1])[0] == 'P':
#                yield t.pop(-1)
#            yield ''.join(t)
#    return ' '.join(tokens())
    s = ''.join(c if ud.category(c)[0] != 'P' else f' {c} ' for c in s)
    return ' '.join(t for t in s.strip().split() if t != PARTITION)

def randomSubmission():
    return r.subreddit('all').random()

def depthPairs(submission, breadthFirst=True):
    submission.comments.replace_more(limit=None)
    cq = deque(zip(submission.comments[:], it.repeat(1)))
    while cq:
        comment, depth = cq.popleft()
        enqueue = cq.extend if breadthFirst else cq.extendleft
        enqueue(zip(comment.replies, it.repeat(depth+1)))
        yield (comment, depth)

def positiveSamples(n=float('inf')):
    i = 0
    while i < n:
        submission = randomSubmission()
        previous = None
        for tail, d_tail in depthPairs(submission, False):
            if previous is None:
                previous = (tail, d_tail)
                continue
            head, d_head = previous
            if d_tail > d_head:
                yield (head, tail)
        i += 1

# return a random comment and its depth
def randomComment(maxDepth=1):
    submission = randomSubmission()
    pairs = []
    while len(pairs) < 1:
        pairs = [(comment, depth)
                 for (comment, depth) in depthPairs(submission, True)
                 if depth <= maxDepth]
    return random.choice(pairs)

# negative sampling — build tuples of unrelated comments
def negativeSamples(n=float('inf')):
    i = 0
    while i < n:
        head, d_head = randomComment()
        tail, d_tail = randomComment()
        if d_head < d_tail:
            # swap 'em
            head, tail = tail, head
        yield (head, tail)
        i += 1

def samples(negativeSkew = 0.5, n=float('inf')):
    negatives = 0
    total = 0
    pq = deque()
    neg = negativeSamples()
    pos = positiveSamples()
    while total < n:
        negative = negatives < negativeSkew * total
        total += 1
        negatives += 1 if negative else 0
        sampler = neg if negative else pos
        yield (negative, next(sampler))

def annotations(n=12500):
    for negative, pair in samples():
        # TODO: Figure out what in the sampling stack keeps givin us empty
        # reply tuples
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
