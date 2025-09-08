# Hashtag Policy

Captions control how content is indexed. Follow these rules when using
hashtags:

1. **One content tag** – exactly one of the supported content hashtags such
   as `#slides`, `#audio` or `#video`.
2. **Order matters** – the recommended order is:
   1. content tag
   2. optional title or description
   3. `#المحاضرة_n` for lecture number when required
   4. `#1446` for the year if applicable
   5. `#الدكتور_الاسم` for the lecturer when applicable
3. **No extra text** before the content tag. Anything after the allowed tags is
   ignored.

## Examples
### Correct
```text
#slides
#المحاضرة_1: الدوائر الكهربائية
#1446
#الدكتور_صالح
```

### Incorrect
```text
#video #slides
#الملزمة
```
The bot will reject these with guidance on the expected order.
