import logging
import re


class RedactResetLinks(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(
            r"(/accounts/reset/)[^/\s]+/[^/\s]+/",
            r"\1[redacted]/[redacted]/",
            record.getMessage(),
        )
        record.args = ()
        return True
