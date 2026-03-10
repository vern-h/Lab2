#!/usr/bin/env python3
import sys

# Input format: UserID1 UserID2 (User1 follows User2)
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    parts = line.split()
    if len(parts) == 2:
        user_a, user_b = parts[0], parts[1]
        # A follows B: A has one more followee (B), B has one more follower (A)
        print(f"{user_a}\tfollowee:1")
        print(f"{user_b}\tfollower:1")