# text_utils.py
# 역할:
#   macOS/Pygame에서 한글 입력이 호환 자모(ㅇㅏㄴ)로 들어오는 경우를 완성형(안)으로 정리합니다.
import unicodedata


CHOSEONG = (
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)
JUNGSEONG = (
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ",
)
JONGSEONG = (
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ",
    "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)

CHOSEONG_INDEX = {char: index for index, char in enumerate(CHOSEONG)}
JUNGSEONG_INDEX = {char: index for index, char in enumerate(JUNGSEONG)}
JONGSEONG_INDEX = {char: index for index, char in enumerate(JONGSEONG) if char}

COMBINED_VOWELS = {
    ("ㅗ", "ㅏ"): "ㅘ",
    ("ㅗ", "ㅐ"): "ㅙ",
    ("ㅗ", "ㅣ"): "ㅚ",
    ("ㅜ", "ㅓ"): "ㅝ",
    ("ㅜ", "ㅔ"): "ㅞ",
    ("ㅜ", "ㅣ"): "ㅟ",
    ("ㅡ", "ㅣ"): "ㅢ",
}
COMBINED_FINALS = {
    ("ㄱ", "ㅅ"): "ㄳ",
    ("ㄴ", "ㅈ"): "ㄵ",
    ("ㄴ", "ㅎ"): "ㄶ",
    ("ㄹ", "ㄱ"): "ㄺ",
    ("ㄹ", "ㅁ"): "ㄻ",
    ("ㄹ", "ㅂ"): "ㄼ",
    ("ㄹ", "ㅅ"): "ㄽ",
    ("ㄹ", "ㅌ"): "ㄾ",
    ("ㄹ", "ㅍ"): "ㄿ",
    ("ㄹ", "ㅎ"): "ㅀ",
    ("ㅂ", "ㅅ"): "ㅄ",
}

LEADING_JAMO_TO_COMPAT = {chr(0x1100 + index): char for index, char in enumerate(CHOSEONG)}
VOWEL_JAMO_TO_COMPAT = {chr(0x1161 + index): char for index, char in enumerate(JUNGSEONG)}
TRAILING_JAMO_TO_COMPAT = {chr(0x11A8 + index - 1): char for index, char in enumerate(JONGSEONG) if char}


def decompose_hangul_to_compat(text):
    chars = []
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            index = code - 0xAC00
            lead = index // 588
            vowel = (index % 588) // 28
            tail = index % 28
            chars.append(CHOSEONG[lead])
            chars.append(JUNGSEONG[vowel])
            if tail:
                chars.append(JONGSEONG[tail])
        elif char in LEADING_JAMO_TO_COMPAT:
            chars.append(LEADING_JAMO_TO_COMPAT[char])
        elif char in VOWEL_JAMO_TO_COMPAT:
            chars.append(VOWEL_JAMO_TO_COMPAT[char])
        elif char in TRAILING_JAMO_TO_COMPAT:
            chars.append(TRAILING_JAMO_TO_COMPAT[char])
        else:
            chars.append(char)
    return chars


def read_vowel(chars, index):
    if index >= len(chars) or chars[index] not in JUNGSEONG_INDEX:
        return "", 0
    vowel = chars[index]
    if index + 1 < len(chars):
        combined = COMBINED_VOWELS.get((vowel, chars[index + 1]))
        if combined:
            return combined, 2
    return vowel, 1


def compose_compat_jamo(chars):
    result = []
    index = 0
    while index < len(chars):
        char = chars[index]
        if char in CHOSEONG_INDEX:
            vowel, vowel_count = read_vowel(chars, index + 1)
            if vowel:
                lead_index = CHOSEONG_INDEX[char]
                vowel_index = JUNGSEONG_INDEX[vowel]
                index += 1 + vowel_count
                tail_index = 0

                if index < len(chars) and chars[index] in JONGSEONG_INDEX:
                    first_tail = chars[index]
                    next_is_vowel = index + 1 < len(chars) and chars[index + 1] in JUNGSEONG_INDEX
                    if not next_is_vowel:
                        combined_tail = ""
                        if index + 1 < len(chars):
                            combined_tail = COMBINED_FINALS.get((first_tail, chars[index + 1]), "")
                        combined_next_is_vowel = index + 2 < len(chars) and chars[index + 2] in JUNGSEONG_INDEX
                        if combined_tail and not combined_next_is_vowel:
                            tail_index = JONGSEONG_INDEX[combined_tail]
                            index += 2
                        else:
                            tail_index = JONGSEONG_INDEX[first_tail]
                            index += 1

                syllable = 0xAC00 + ((lead_index * 21 + vowel_index) * 28) + tail_index
                result.append(chr(syllable))
                continue

        result.append(char)
        index += 1

    return "".join(result)


def normalize_korean_text(value):
    text = unicodedata.normalize("NFC", str(value or ""))
    return unicodedata.normalize("NFC", compose_compat_jamo(decompose_hangul_to_compat(text)))
