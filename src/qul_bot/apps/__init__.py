"""Reading mobile app builds (Android .apk, iOS .ipa) without any external tools.

Everything here works on bytes in memory, treats the input as hostile (size caps, no
extraction to disk) and knows nothing about Telegram.
"""
