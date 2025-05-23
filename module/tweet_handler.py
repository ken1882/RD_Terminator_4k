from tweety.types.twDataTypes import Tweet

def filter_ffxiv_recruits(tweet: Tweet) -> bool:
    """
    Filters out tweets that are recruitment posts for FFXIV FCs.
    True if keep, False if discard.
    """
    kws = ('メンバー', '募集', 'FC', 'FCPR20')
    msg = tweet['message']
    score = 0
    for k in kws:
        if k in msg:
            score += 1
    return score < 2
