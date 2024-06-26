"""Code coverage for repositories."""

import logging
import re
from typing import Optional

import requests

from sitreps_client.exceptions import CodeCoverageError
from sitreps_client.exceptions import SitrepsError
from sitreps_client.utils.ci_downloader import CIDownloader
from sitreps_client.utils.helpers import wait_for

LOGGER = logging.getLogger(__name__)


class CodecovCoverage:
    """Code coverage from codecov.io."""

    CODECOV_BRANCH_BASE = "https://codecov.io/api/gh/{repo_slug}/branch/{branch}?limit=1"
    CODECOV_WEB_BASE = "https://codecov.io/gh/{repo_slug}/branch/{branch}/graph/badge.svg"

    def __init__(self, repo_slug: str, branch: str = "master"):
        self.repo_slug = repo_slug
        self.branch = branch

    @property
    def is_available(self) -> bool:
        """Check if coverage data exists for given repository.

        Try to download badge icon and check its status text.
        """
        response, err, *__ = wait_for(
            lambda: requests.get(
                self.CODECOV_WEB_BASE.format(repo_slug=self.repo_slug, branch=self.branch)
            ),
            delay=1,
            num_sec=3,
            ignore_falsy=True,
        )
        if err or not response:
            LOGGER.warning(f"Coverage data is unavailable for '{self.repo_slug}:{self.branch}'")
            return False

        return ">unknown</text>" not in response.text

    def get_coverage(self) -> Optional[float]:
        """Get coverage info for the branch."""
        response, err, *__ = wait_for(
            lambda: requests.get(
                self.CODECOV_BRANCH_BASE.format(repo_slug=self.repo_slug, branch=self.branch)
            ),
            delay=2,
            num_sec=7,
        )
        if err:
            msg = f'Failed to get code coverage for repo "{self.repo_slug}", failure: {str(err)}'
            LOGGER.error(msg)
            raise CodeCoverageError(msg)

        if not (response or response.ok):
            msg = f'Failed to download log for repo "{self.repo_slug} "' f"[{response.text}]"
            LOGGER.error(msg)
            raise CodeCoverageError(msg)

        response_json = response.json()
        if response_json.get("commit", {}).get("totals", {}):
            coverage_ratio_str = response_json.get("commit", {}).get("totals", {}).get("c")
        elif response_json.get("commits", []):
            coverage_ratio_str = response_json["commits"][0].get("totals", {}).get("c")
        else:
            coverage_ratio_str = None
        if coverage_ratio_str is None:
            return None
        coverage_ratio = float(coverage_ratio_str)
        return coverage_ratio

    def __repr__(self):
        return f"<CodecovCoverage(repo_slug={self.repo_slug})>"


def get_regex_cov(pattern: str, string: str) -> Optional[float]:
    """Return coverage matched by regex pattern."""
    match = re.search(pattern, string)
    if match is None:
        return None

    try:
        return float(match.group(1))
    except (IndexError, ValueError) as err:
        LOGGER.warning("Coverage, failure: %s", str(err))
        return None


def get_htmlcov(string: str) -> Optional[float]:
    """Return coverage from "htmlcov" index.html generated by Coverage.py."""
    return get_regex_cov('<span class="pc_cov">([0-9]+)%</span>', string)


class CICoverage:
    """Code coverage from CI log (Jenkins, ...).

    Args:
        url (str): CI raw link (eg. jenkins job raw link)
        ci_downloader (CIDownloader): Instance of CI downloader (eg. JenkinsDownloader)
        pattern (str, optional): Match pattern
    """

    def __init__(self, url: str, ci_downloader: CIDownloader, pattern: Optional[str] = None):
        self.url = url
        self.ci_downloader = ci_downloader
        self.pattern = pattern

    def get_coverage(self) -> Optional[float]:
        """Get coverage info."""
        try:
            string = self.ci_downloader.get_text(self.url)
        except SitrepsError as err:
            LOGGER.warning(f"Failed to get code coverage for url {self.url}, error: {str(err)}")
            raise CodeCoverageError(
                f"Failed to get code coverage for url {self.url}, error: {str(err)}"
            )

        if not self.pattern:
            return get_htmlcov(string)
        return get_regex_cov(self.pattern, string)

    def __repr__(self):
        return f"<CICoverage(url={self.url})>"


def get_code_coverage(repo_slug: str, branch: str = "master") -> Optional[float]:
    """Get code coverage from codecov.io

    Args:
        repo_slug (str): Repository slug
        branch (str, optional): Branch for which Code Coverage fetch. Defaults to "master".

    Returns:
        Optional[float]: code coverage
    """
    code_cov = CodecovCoverage(repo_slug=repo_slug, branch=branch)
    # TODO: Add CICoverage facility.
    if code_cov.is_available:
        return code_cov.get_coverage()
    return None
