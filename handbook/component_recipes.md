# Component Recipes

## APPROXIMATE_DATE

- Common validator types: MANDATORY

- Common hints: MIN_ACUITY_YEARS, MIN_ACUITY_WEEKS

- Common flags: BLUE

Example CIR:

```json

{
  "kind": "item",
  "type": "APPROXIMATE_DATE",
  "text": "APPROXIMATE_DATE example",
  "hints": [
    "MIN_ACUITY_YEARS",
    "MIN_ACUITY_WEEKS"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## APPROXIMATE_DURATION

- Common validator types: MANDATORY

- Common hints: MIN_ACUITY_WEEKS

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "APPROXIMATE_DURATION",
  "text": "APPROXIMATE_DURATION example",
  "hints": [
    "MIN_ACUITY_WEEKS"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## ASSESSMENT

- Common validator types: —

- Common hints: —

- Common flags: RED

Example CIR:

```json

{
  "kind": "item",
  "type": "ASSESSMENT",
  "text": "ASSESSMENT example"
}

```

## BILL

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "BILL",
  "text": "BILL example"
}

```

## CHECKBOX

- Common validator types: MANDATORY, SCRIPT

- Common hints: USE_BUTTONS_FOR_MENU, SAME_LINE

- Common flags: BLUE, RED

Example CIR:

```json

{
  "kind": "item",
  "type": "CHECKBOX",
  "text": "CHECKBOX example",
  "hints": [
    "USE_BUTTONS_FOR_MENU",
    "SAME_LINE"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## DATE

- Common validator types: MANDATORY, SCRIPT

- Common hints: —

- Common flags: BLUE

Example CIR:

```json

{
  "kind": "item",
  "type": "DATE",
  "text": "DATE example",
  "validator": {
    "type": "MANDATORY"
  }
}

```

## DIAGRAM

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "DIAGRAM",
  "text": "DIAGRAM example"
}

```

## FILE_UPLOAD

- Common validator types: MANDATORY

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "FILE_UPLOAD",
  "text": "FILE_UPLOAD example",
  "validator": {
    "type": "MANDATORY"
  }
}

```

## FINDING

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "FINDING",
  "text": "FINDING example"
}

```

## FORMULA

- Common validator types: —

- Common hints: USE_BUTTONS_FOR_MENU, JS_MENU_OPTION, SAME_LINE

- Common flags: BLUE, ORANGE

Example CIR:

```json

{
  "kind": "item",
  "type": "FORMULA",
  "text": "FORMULA example",
  "hints": [
    "USE_BUTTONS_FOR_MENU",
    "JS_MENU_OPTION"
  ]
}

```

## IX

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "IX",
  "text": "IX example"
}

```

## LABEL

- Common validator types: SCRIPT

- Common hints: VERTICAL_STACKING, INDIVIDUAL_MENU_OPTION, JS_MENU_OPTION, USE_BUTTONS_FOR_MENU

- Common flags: RED, GREEN

Example CIR:

```json

{
  "kind": "item",
  "type": "LABEL",
  "text": "LABEL example",
  "hints": [
    "VERTICAL_STACKING",
    "INDIVIDUAL_MENU_OPTION"
  ],
  "validator": {
    "type": "SCRIPT"
  }
}

```

## MENU

- Common validator types: MANDATORY

- Common hints: USE_BUTTONS_FOR_MENU, VERTICAL_STACKING, SAME_LINE, USE_DROPDOWN_MENU, BORDER

- Common flags: RED, GREEN

Example CIR:

```json

{
  "kind": "item",
  "type": "MENU",
  "text": "MENU example",
  "hints": [
    "USE_BUTTONS_FOR_MENU",
    "VERTICAL_STACKING"
  ],
  "validator": {
    "type": "MANDATORY"
  },
  "choices": [
    {
      "val": "A",
      "display": "A"
    },
    {
      "val": "B",
      "display": "B"
    },
    {
      "val": "C",
      "display": "C"
    }
  ]
}

```

## MENU_MULTI_SELECT

- Common validator types: MANDATORY

- Common hints: USE_BUTTONS_FOR_MENU, VERTICAL_STACKING, SAME_LINE

- Common flags: BLUE, ORANGE

Example CIR:

```json

{
  "kind": "item",
  "type": "MENU_MULTI_SELECT",
  "text": "MENU_MULTI_SELECT example",
  "hints": [
    "USE_BUTTONS_FOR_MENU",
    "VERTICAL_STACKING"
  ],
  "validator": {
    "type": "MANDATORY"
  },
  "choices": [
    {
      "val": "A",
      "display": "A"
    },
    {
      "val": "B",
      "display": "B"
    },
    {
      "val": "C",
      "display": "C"
    }
  ]
}

```

## NO_YES_NOT_SURE

- Common validator types: —

- Common hints: —

- Common flags: YELLOW

Example CIR:

```json

{
  "kind": "item",
  "type": "NO_YES_NOT_SURE",
  "text": "NO_YES_NOT_SURE example"
}

```

## NUMERIC_SCALE

- Common validator types: MANDATORY

- Common hints: USE_BUTTONS_FOR_MENU

- Common flags: YELLOW

Example CIR:

```json

{
  "kind": "item",
  "type": "NUMERIC_SCALE",
  "text": "NUMERIC_SCALE example",
  "hints": [
    "USE_BUTTONS_FOR_MENU"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## PE_CHECK

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "PE_CHECK",
  "text": "PE_CHECK example"
}

```

## PE_TEST

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "PE_TEST",
  "text": "PE_TEST example"
}

```

## PICTURE

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "PICTURE",
  "text": "PICTURE example"
}

```

## PROPOSITION

- Common validator types: MANDATORY, SCRIPT

- Common hints: USE_BUTTONS_FOR_MENU

- Common flags: RED, YELLOW

Example CIR:

```json

{
  "kind": "item",
  "type": "PROPOSITION",
  "text": "PROPOSITION example",
  "hints": [
    "USE_BUTTONS_FOR_MENU"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## RX

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "RX",
  "text": "RX example"
}

```

## SECTION

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "SECTION",
  "text": "SECTION example"
}

```

## TEXT_AREA

- Common validator types: MANDATORY, SCRIPT

- Common hints: SAME_LINE, USE_BUTTONS_FOR_MENU

- Common flags: BLUE, RED

Example CIR:

```json

{
  "kind": "item",
  "type": "TEXT_AREA",
  "text": "TEXT_AREA example",
  "hints": [
    "SAME_LINE",
    "USE_BUTTONS_FOR_MENU"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## TEXT_FIELD

- Common validator types: MANDATORY, PHONE, EMAIL

- Common hints: SAME_LINE, USE_BUTTONS_FOR_MENU, VERTICAL_STACKING, INDIVIDUAL_MENU_OPTION

- Common flags: BLUE, RED

Example CIR:

```json

{
  "kind": "item",
  "type": "TEXT_FIELD",
  "text": "TEXT_FIELD example",
  "hints": [
    "SAME_LINE",
    "USE_BUTTONS_FOR_MENU"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## TEXT_FIELD_NUMERIC

- Common validator types: MANDATORY, REG_EXP, SCRIPT

- Common hints: SAME_LINE

- Common flags: ORANGE

Example CIR:

```json

{
  "kind": "item",
  "type": "TEXT_FIELD_NUMERIC",
  "text": "TEXT_FIELD_NUMERIC example",
  "hints": [
    "SAME_LINE"
  ],
  "validator": {
    "type": "MANDATORY"
  }
}

```

## TIME

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "TIME",
  "text": "TIME example"
}

```

## TX

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "TX",
  "text": "TX example"
}

```

## VIDEO

- Common validator types: —

- Common hints: —

- Common flags: —

Example CIR:

```json

{
  "kind": "item",
  "type": "VIDEO",
  "text": "VIDEO example"
}

```