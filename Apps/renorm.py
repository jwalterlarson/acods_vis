"""
def renormalisationRequired(FieldTag):
"""
    """
    Boolean function to determine whether a field requires renormalisation.
    """
    if FieldTag in fieldTagsToRenormCoeffs.keys():
        return True
    else:
        return False

