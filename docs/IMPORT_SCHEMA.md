# Import/Export Schema

This document describes the JSON structure used by the `import_export`
module for bulk transfer of taxonomy data.  The file mirrors the order in
which tables are processed during export and import.

## Top-level structure

```json
{
  "sections": [...],
  "cards": [...],
  "item_types": [...],
  "aliases": [...],
  "mappings": [...],
  "subject_section_enable": [...],
  "presets": [... optional ...]
}
```

Each key contains a list of objects representing rows in the respective
database table.  Keys appear in the order above so that foreign-key references (e.g. card → section) can be resolved during import.

## Example
```json
{
  "sections": [{"key": "theory", "label_ar": "نظري", "label_en": "Theory", "is_enabled": 1, "sort_order": 0}],
  "cards": [{"key": "slides", "label_ar": "سلايدات", "label_en": "Slides", "section": "theory", "show_when_empty": 0, "is_enabled": 1, "sort_order": 0}],
  "item_types": [],
  "aliases": [],
  "mappings": [],
  "subject_section_enable": [],
  "presets": []
}
```


### sections

```json
{
  "key": "theory",
  "label_ar": "نظري",
  "label_en": "Theory",
  "is_enabled": 1,
  "sort_order": 0
}
```

### cards

The `section` field refers to the section `key`.

```json
{
  "key": "slides",
  "label_ar": "سلايدات",
  "label_en": "Slides",
  "section": "theory",
  "show_when_empty": 0,
  "is_enabled": 1,
  "sort_order": 0
}
```

### item_types

```json
{
  "key": "pdf",
  "label_ar": "بي دي اف",
  "label_en": "PDF",
  "requires_lecture": 0,
  "allows_year": 1,
  "allows_lecturer": 1,
  "is_enabled": 1,
  "sort_order": 0
}
```

### aliases

```json
{
  "alias": "hw",
  "normalized": "hw",
  "lang": null
}
```

### mappings

Mappings link an alias to a target entity.  `target_kind` and
`target_id` are implementation specific.  The example below maps the
alias `hw` to card id `1`.

```json
{
  "alias": "hw",
  "target_kind": "card",
  "target_id": 1,
  "is_content_tag": 0,
  "overrides": null
}
```

### subject_section_enable

```json
{
  "subject_id": 1,
  "section": "theory",
  "is_enabled": 1,
  "sort_order": 0
}
```

### presets (optional)

The `presets` key is reserved for future use.  When present it should be
an array; the current implementation ignores its contents.
