"""Signal handlers for the NetCracker SSoT integration.

Registers the integration's jobs with the nautobot-app-ssot framework
so they appear in the SSoT dashboard and data source list.
"""

import logging

logger = logging.getLogger(__name__)


def register_jobs(sender, **kwargs):
    """Register NetCracker jobs with the nautobot-app-ssot framework.

    Connected to the nautobot_ssot post_migrate / ready signal so the
    integration shows up in the SSoT UI without requiring manual registration.
    """
    try:
        from nautobot_ssot.utils import register_datasource

        from nautobot_ssot_netcracker.jobs import NetCrackerDataSource

        register_datasource(NetCrackerDataSource)
        logger.debug("NetCracker SSoT: registered NetCrackerDataSource.")
    except ImportError:
        # nautobot-app-ssot may not expose register_datasource in all versions;
        # jobs are also discovered automatically via the plugin entrypoint.
        logger.debug("NetCracker SSoT: register_datasource not available — relying on entrypoint registration.")
    except Exception as exc:
        logger.warning("NetCracker SSoT: failed to register data source: %s", exc)
