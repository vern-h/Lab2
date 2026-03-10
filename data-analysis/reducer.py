#!/usr/bin/env python3
import sys

current_user = None
counts = {"follower": 0, "followee": 0}

for line in sys.stdin:
    line = line.strip()
    user, data = line.split('\t')
    type_info, count = data.split(':')
    count = int(count)

    if current_user == user:
        counts[type_info] += count
    else:
        if current_user:
            # Output results for the previous user
            print(f"{current_user}\tfollowers:{counts['follower']}\tfollowees:{counts['followee']}")
        
        current_user = user
        counts = {"follower": 0, "followee": 0}
        counts[type_info] = count

# print out the last user
if current_user:
    print(f"{current_user}\tfollowers:{counts['follower']}\tfollowees:{counts['followee']}")