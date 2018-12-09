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

def sanitize(s: str):
    s = ''.join(c if ud.category(c)[0] != 'P' else f' {c} ' for c in s)
    return ' '.join(t for t in s.strip().split() if t != PARTITION)

def randomSubmission():
    return r.subreddit('all').random()

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
def randomComments(poolSize=300, maxDepth=2, n=float('inf')):
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
def negativeSamples(rnd=randomComments(), n=float('inf')):
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
REMOVED = {'[removed]', '[deleted]'}
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
        head, tail = next(sampler)
        if head.body in REMOVED or tail.body in REMOVED:
            continue
        yield (negative, next(sampler))

def annotations(startbytes=0, bytes=(120<<20), progress=lambda x: None, encoding='utf-8'):
    bytelength = startbytes
    for negative, pair in samples():
        head, tail = pair
        call = sanitize(head.body)
        response = sanitize(tail.body)
        label = 'negative' if negative else 'positive'
        yield f'__label__{label} {call} {PARTITION} {response}'
        try:
            read = len(call.encode(encoding)) + len(response.encode(encoding))
        except UnicodeEncodeError:
            read = len(call) + len(response)
        bytelength += read
        got = bytelength / bytes
        progress(got)
        if got > 1:
            break

if __name__ == '__main__':
    from humanfriendly import parse_size
    from sys import argv, stdout, stderr
    from argparse import ArgumentParser
    from os import SEEK_END
    desc = ('Retrieve fastText supervised mutual-relevance'
            ' data from various subreddits')
    parser = ArgumentParser(description=desc)
    parser.add_argument(
        '--opath',
        help='Path to the training file',
        required=False)
    parser.add_argument(
        '--length',
        help='Size of the data-set to be retrieved (KB, G, etc.)',
        default='120M',
        required=False)
    parser.add_argument(
        '--silent',
        default=False,
        type=bool)
    parser.add_argument(
        '--encoding',
        default='utf-8')

    parsed = parser.parse_args()
    parsed.length = parse_size(parsed.length)

    spinner_index = 0
    SPINNER = '⣾⣽⣻⢿⡿⣟⣯⣷' if parsed.encoding.find('utf-') >= 0 else '.oO@*'
    def progress(x):
        global spinner_index
        c = SPINNER[spinner_index]
        if not parsed.silent:
            bar = '#' * round(x * 40) + ' ' * (40 - round(x * 40))
            stderr.write(f'{x*100:2.02f}% [{bar}] {c}\r')
        spinner_index += 1
        spinner_index %= len(SPINNER)

    startbytes = 0
    ostream = stdout.buffer if parsed.opath is None else open(parsed.opath, 'wb')
    with ostream as o:
        if o is not stdout.buffer:
            o.seek(0, SEEK_END)
            startbytes = o.tell()

        data = annotations(startbytes, parsed.length, progress, parsed.encoding)
        data = (f'{ln}\r\n' for ln in data)
        try:
            for ln in data:
                o.write(ln.encode(parsed.encoding))
        except KeyboardInterrupt:
            pass
