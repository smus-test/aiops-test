"""Runs the SageMaker Pipeline for Marketing Classification with MLflow integration."""
import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-name", type=str, required=True)
    parser.add_argument("--role-arn", type=str, required=True)
    parser.add_argument("--tags", type=str, default=None)
    parser.add_argument("--kwargs", type=str, default=None)
    parser.add_argument("--pipeline-name", type=str, default=None)
    parser.add_argument("--log-level", type=str, default=None)
    parser.add_argument("--mlflow-tracking-arn", type=str, default=None)
    args = parser.parse_args()

    if args.log_level is not None:
        level = logging.getLevelName(args.log_level.upper())
        logger.setLevel(level)

    tags = json.loads(args.tags) if args.tags is not None else []

    try:
        module = __import__(args.module_name, fromlist=["get_pipeline"])
        get_pipeline = getattr(module, "get_pipeline")
    except Exception as e:
        logger.error(f"Failed to import the module {args.module_name}: {e}")
        sys.exit(1)

    kwargs = json.loads(args.kwargs) if args.kwargs is not None else {}
    
    # Add MLflow tracking ARN to kwargs if provided
    if args.mlflow_tracking_arn:
        kwargs["mlflow_tracking_arn"] = args.mlflow_tracking_arn

    logger.info("Getting pipeline")
    pipeline = get_pipeline(**kwargs)

    if args.pipeline_name is not None:
        pipeline.name = args.pipeline_name

    logger.info(f"Creating/updating pipeline: {pipeline.name}")
    pipeline.upsert(role_arn=args.role_arn, tags=tags)

    logger.info("Starting pipeline execution")
    execution = pipeline.start()

    logger.info(f"Pipeline {pipeline.name} successfully created/updated and started")
    logger.info(f"Pipeline execution ARN: {execution.arn}")


if __name__ == "__main__":
    main()
