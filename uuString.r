# \file
# \brief     UU - String functions.
# \author    Chris Smeele, Ton Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# \brief Chop part of a string based on a split character.
#
# if leftToRight is true, *head will contain *string up to the first *splitChar,
# and *tail will contain the rest of the string.
# Otherwise, *tail will contain the part of the string from the last *splitChar.
# and *head will contain the rest of the string.
#
# *string is not modified.
#
# \param[in]  string
# \param[out] head
# \param[out] tail
# \param[in]  splitChar   the character on which to split the string
# \param[in]  leftToRight true if we should chop from the left side
#
uuChop(*string, *head, *tail, *splitChar, *leftToRight) {
	if (*string like "**splitChar*") {
		if (*leftToRight) {
			*tail =  triml(*string, *splitChar);
			*head = substr(*string, 0, strlen(*string) - strlen(*tail) - 1);
		} else {
			*head =  trimr(*string, *splitChar);
			*tail = substr(*string, strlen(*head) + 1, strlen(*string));
		}
	} else {
		# No *splitChar in *string.
		*head = if *leftToRight then ""      else *string;
		*tail = if *leftToRight then *string else "";
	}
}

# \brief Split a file name into a base name and a file extension.
#
# \param[in]  fileName
# \param[out] baseName
# \param[out] extension
#
uuChopFileExtension(*fileName, *baseName, *extension) {
	uuChop(*fileName, *baseName, *extension, ".", false);
}

# \brief Split a path into a base name and a path.
#
# \param[in]  fileName
# \param[out] parent
# \param[out] baseName
#
uuChopPath(*path, *parent, *baseName) {
	if (*path like regex "^/[^/]*$") {
		# *path is "/" or a top level directory.
		*baseName = if strlen(*path) > 1 then substr(*path, 1, strlen(*path)) else "/";
		*parent   = "/";
	} else {
		uuChop(*path, *parent, *baseName, "/", false);
	}
}

# \brief Split a checksum into a checksum type and a value
#
# \param[in]  checksum
# \param[out] checksumType  e.g. "md5" or "sha2" 
# \param[out] checksumValue
#
uuChopChecksum(*checksum, *checksumType, *checksumValue) {
# if checksum is not labeled then it is "md5"
   *checksumType = "md5";
   *checksumValue = *checksum;
   *checksumParts = split(*checksum, ":");
   if (size(*checksumParts) > 1 ) { 
      *checksumType = hd(*checksumParts);
      *checksumValue = ""; 
      foreach (*value in tl(*checksumParts)) {
         *checksumValue = "*checksumValue*value";
      }
   }
}

# \brief Convert a string to uppercase characters
# \param[in]	strIn
# \param[out]	strOut
#
uuStrToUpper(*strIn, *strOut) {
	uuStrShift(*strIn, *strOut, "upper");
}

# \brief Convert a string to lowercase characters
# \param[in]	strIn
# \param[out]	strOut
#
uuStrToLower(*strIn, *strOut) {
	uuStrShift(*strIn, *strOut, "lower");
}

# \brief (internal function) Convert a string to lowercase or uppercase
# \param[in]	strIn
# \param[out]	strOut
# \param[in]	toCase	should be either "lower" or "upper"
#
uuStrShift(*strIn, *strOut, *toCase) {
	*strOut = ''; 
	for (*pos = 0; *pos < strlen(*strIn); *pos = *pos + 1) {
		*c = substr(*strIn, *pos, *pos + 1);
		uuChrShift(*c, *toCase);
		*strOut = *strOut ++ *c;
	}
}

# \brief Convert a single characterstring to lowercase or uppercase
# \param[in/out]	strIn
# \param[in]		toCase	should be either "lower" or "upper"	
#
uuChrShift(*c, *toCase) {
	*a1 = split("a b c d e f g h i j k l m n o p q r s t u v w x y z", " ");
	*a2 = split("A B C D E F G H I J K L M N O P Q R S T U V W X Y Z", " ");
	# assume transformation to uppercase
	*aSource = *a1;
	*aDestination = *a2;
	if (*toCase == "lower") {
		*aSource = *a2;
		*aDestination = *a1;
	}
	*element = 0;
	foreach (*source in *aSource) {
		if (*c == *source) {
			*c = elem(*aDestination, *element);
			break;
		}
		*element = *element + 1;
	}
} 

