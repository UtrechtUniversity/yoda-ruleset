import re


def correctify_orcid(org_orcid):
    """Correct illformatted ORCID."""
    # Get rid of all spaces.
    orcid = org_orcid.replace(' ', '')

    # Upper-case X.
    orcid = orcid.replace('x', 'X')

    # The last part should hold a valid id like eg: 1234-1234-1234-123X.
    # If not, it is impossible to correct it to the valid orcid format
    orcs = orcid.split('/')
    if not re.search("^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcs[-1]):
        return None

    return "https://orcid.org/{}".format(orcs[-1])


def correctify_scopus(org_scopus):
    """Correct illformatted Scopus."""
    # Get rid of all spaces.
    new_scopus = org_scopus.replace(' ', '')

    if not re.search("^\d{1,11}$", new_scopus):
        return None

    return new_scopus


def correctify_isni(org_isni):
    """Correct ill-formatted ISNI."""
    # Remove all spaces.
    new_isni = org_isni.replace(' ', '')

    # Upper-case X.
    new_isni = new_isni.replace('x', 'X')

    # The last part should hold a valid id like eg: 123412341234123X.
    # If not, it is impossible to correct it to the valid isni format
    new_isni = new_isni.split('/')
    if not re.search("^[0-9]{15}[0-9X]$", new_isni[-1]):
        return None

    return "https://isni.org/isni/{}".format(new_isni[-1])


def correctify_researcher_id(org_researcher_id):
    """Correct illformatted ResearcherID."""
    # Get rid of all spaces.
    researcher_id = org_researcher_id.replace(' ', '')

    # The last part should hold a valid id like eg: A-1234-1234
    # If not, it is impossible to correct it to the valid ResearcherID format
    orcs = researcher_id.split('/')
    if not re.search("^[A-Z]-[0-9]{4}-[0-9]{4}$", orcs[-1]):
        # Return original value.
        return org_researcher_id

    return "https://www.researcherid.com/rid/{}".format(orcs[-1])
