from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="productboard-sync",
        description="Sync Productboard data to CSV files in local/OneDrive/SharePoint storage.",
    )
    parser.add_argument(
        "--entity",
        dest="entities",
        action="append",
        metavar="ENTITY",
        help="Entity type to sync (repeatable). Defaults to SYNC_ENTITIES config / all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and transform data but do not write to storage.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: config LOG_LEVEL or INFO).",
    )
    args = parser.parse_args()

    from productboard_sync.config import ALL_ENTITY_TYPES, get_settings, get_storage_backend
    from productboard_sync.productboard.client import ProductboardClient
    from productboard_sync.sync.runner import SyncRunner
    from productboard_sync.utils.logging import setup_logging

    try:
        settings = get_settings()
        setup_logging(args.log_level or settings.log_level)
        logger = logging.getLogger(__name__)

        if args.entities:
            if len(args.entities) == 1 and args.entities[0].lower() == "all":
                entity_types = ALL_ENTITY_TYPES
            else:
                invalid = [e for e in args.entities if e not in ALL_ENTITY_TYPES]
                if invalid:
                    parser.error(f"Unknown entity type(s): {invalid}")
                entity_types = args.entities
        else:
            entity_types = settings.sync_entities

        client = ProductboardClient(settings.productboard_api_key, timeout=settings.request_timeout)
        backend = get_storage_backend(settings)
        runner = SyncRunner(client, backend)
        runner.run(entity_types, dry_run=args.dry_run)
        logger.info("Sync complete.")
    except Exception:
        logging.getLogger(__name__).exception("Sync failed with an unhandled exception.")
        sys.exit(1)


if __name__ == "__main__":
    main()
