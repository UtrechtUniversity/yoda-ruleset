Coding guidelines for Yoda rules
================================

Guideline           | Rule
------------------- | -----------------------------------------------------------------------------
Variable names      | camelCase, descriptive (avoid abbrevs)
Function names      | camelCase, start with `uu`. Youth Cohort specific rules start with `uuYc`.
Function parameters | Input parameters first, output parameters last
Whitespace          | Use tabs to indicate indentation level, spaces for alignment
Braces              | Opening brace on the same line as the `if`, `foreach`, ... and function names
Parentheses         | Spaces around parenthesis-enclosed blocks, except for function calls (see example)
Documentation       | Docblocks for every file and every function (see example)
Line length         | Manual line breaks at or before column 120
Line endings        | LF (Unix EOLs) only. The last line in a file always has an EOL character.

Example rule file
-----------------

*Note: Variable and function names should always be descriptive, the example
below is purely to demonstrate the formatting guidelines.*

```
# \file      uuFilename.r
# \brief     Description of this file.
# \author    Author Name 1
# \author    Author Name 2
# \author    Author Name 3
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.txt.

# \brief Short function description here.
#
# Optional detailed function documentation here.
#
# \param[in] paramIn1 parameter description here
# \param[in] paramIn2 parameter description here
# \param[in,out] paramOut1 parameter description here
#
uuFunctionName(*paramIn1, *paramIn2, *paramOut1) {
	if (*paramIn1 == *paramIn2) {
		msiDoSomething();
	} else {
		msiDoSomething();
	}
	if (
		   *paramIn1 == *paramIn2
		|| *paramIn1 == *paramIn2
		|| *paramIn1 == *paramIn2
	) {
		*paramOut1 = "Some value" ++ " some other value";
	}
}

# \brief This function does something.
#
# \param[in] paramIn1 yada yada
# \param[in] paramIn2 yada yada
# \param[in] paramIn3 yada yada
# \param[in] paramIn4 yada yada
#
uuFunctionNameWithALotOfParameters(
	*paramIn1,
	*paramIn2,
	*paramIn3,
	*paramIn4
) {
	uuFunctionNameWithALotOfParameters(
		"Some string value",
		2,
		"Some string value",
		4
	);
	
	*localVariable = 0;

	foreach (*item in *someList) {
		uuFunctionName("Some string", *item, *localVariable);
	}
}
```
