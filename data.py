import praw
import random
import emot
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
    # TODO: Better URI tokenization, handle emotes
    # PUNCT_RGX.sub(s, ' \\1 ')
    # def tokens():
    #     for t in s.split():
    #         if URI_RGX.match(s):
    #             yield s
    #         else:
    #             cq = ''
    #             for c in s:
    #                 if ud.category(c)[0] == 'P':
    #                     yield cq
    #                     yield c
    #                 cq += c
    #
    #     splitp = lambda c: ud.category(c) == 'P' && c
    #     for t in s.split():
    #         t = list(t)
    #         if ud.category(t[0])[0] == 'P':
    #             yield t.pop(0)
    #         if ud.category(t[-1])[0] == 'P':
    #             yield t.pop(-1)
    #         yield ''.join(t)
    # return ' '.join(tokens())
    s = ''.join(c if ud.category(c)[0] != 'P' else f' {c} ' for c in s)
    return ' '.join(t for t in s.strip().split() if t != PARTITION)

def randomSubmission():
    return r.subreddit('random').random()

def depthPairs(submission, n=float('inf'), maxDepth=float('inf'), breadthFirst=True):
    limit = None if n == float('inf') else n
    submission.comments.replace_more(limit=n)
    cq = deque(zip(submission.comments[:], it.repeat(1)))
    i = 0
    while cq:
        comment, depth = cq.popleft()
        enqueue = cq.extend if breadthFirst else cq.extendleft
        yield (comment, depth)
        i += 1
        if depth == maxDepth or i == n:
            break
        enqueue(zip(comment.replies, it.repeat(depth+1)))

def positiveSamples(n=float('inf'), maxDepth=3):
    i = 0
    while i < n:
        submission = randomSubmission()
        previous = None
        for tail, d_tail in depthPairs(submission, n, maxDepth, False):
            if previous is None:
                previous = (tail, d_tail)
                continue
            head, d_head = previous
            if d_tail > d_head:
                yield (head, tail)
        i += 1

# generate random comments
def randomComments(poolSize=50, maxDepth=2, n=float('inf')):
    i = 0
    while i < n:
        cq = deque()
        while len(cq) < poolSize:
            post = randomSubmission()
            added = len(cq)
            pairs = depthPairs(post, poolSize//3, maxDepth, True)
            cq.extend(pairs)
            added = len(cq) - added
            i += added
        random.shuffle(cq)
        yield from cq

# negative sampling — build tuples of unrelated comments
def negativeSamples(rnd=randomComments(3), n=float('inf')):
    i = 0
    while i < n:
        head, d_head = next(rnd)
        tail, d_tail = next(rnd)
        if d_head < d_tail:
            # swap 'em
            head, tail = tail, head
        yield (head, tail)
        i += 1

# aggregate samples with the proportion of negative sampling given in
# negativeSkew, and return them for a count of n
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
