from typing import List, Optional

import strawberry
from strawberry.types import Info

from phoenix.core.model_schema import REFERENCE, ScalarDimension

from ..context import Context
from ..input_types.Granularity import Granularity
from ..input_types.TimeRange import TimeRange
from .DataQualityMetric import DataQualityMetric
from .DimensionDataType import DimensionDataType
from .DimensionType import DimensionType
from .node import Node
from .ScalarDriftMetricEnum import ScalarDriftMetric
from .TimeSeries import (
    DataQualityTimeSeries,
    DriftTimeSeries,
    ensure_timeseries_parameters,
    get_data_quality_timeseries_data,
    get_drift_timeseries_data,
)


@strawberry.type
class Dimension(Node):
    name: str = strawberry.field(description="The name of the dimension (a.k.a. the column name)")
    type: DimensionType = strawberry.field(
        description="Whether the dimension represents a feature, tag, prediction, or actual."
    )
    dataType: DimensionDataType = strawberry.field(
        description="The data type of the column. Categorical or numeric."
    )
    dimension: strawberry.Private[ScalarDimension]

    @strawberry.field
    def drift_metric(
        self,
        info: Info[Context, None],
        metric: ScalarDriftMetric,
        time_range: Optional[TimeRange] = None,
    ) -> Optional[float]:
        """
        Computes a drift metric between all reference data and the primary data
        belonging to the input time range (inclusive of the time range start and
        exclusive of the time range end). Returns None if no reference dataset
        exists, if no primary data exists in the input time range, or if the
        input time range is invalid.
        """
        model = info.context.model
        if model[REFERENCE].empty:
            return None
        time_range, granularity = ensure_timeseries_parameters(model, time_range)
        data = get_drift_timeseries_data(self.dimension, metric, time_range, granularity)
        return data[0].value if len(data) else None

    @strawberry.field
    async def data_quality_metric(
        self,
        info: Info[Context, None],
        metric: DataQualityMetric,
        time_range: Optional[TimeRange] = None,
    ) -> Optional[float]:
        time_range, granularity = ensure_timeseries_parameters(info.context.model, time_range)
        data = get_data_quality_timeseries_data(self.dimension, metric, time_range, granularity)
        return data[0].value if len(data) else None

    @strawberry.field(
        description=(
            "Returns the observed categories of a categorical dimension (usually a dimension of"
            " string values) as a list of unique string labels sorted in lexicographical order."
            " Missing values are excluded. Non-categorical dimensions return an empty list."
        )
    )  # type: ignore  # https://github.com/strawberry-graphql/strawberry/issues/1929
    def categories(self) -> List[str]:
        return list(self.dimension.categories)

    @strawberry.field(
        description=(
            "Returns the time series of the specified metric for data within a time range. Data"
            " points are generated starting at the end time and are separated by the sampling"
            " interval. Each data point is labeled by the end instant and contains data from their"
            " respective evaluation windows."
        )
    )  # type: ignore  # https://github.com/strawberry-graphql/strawberry/issues/1929
    def data_quality_time_series(
        self,
        info: Info[Context, None],
        metric: DataQualityMetric,
        time_range: TimeRange,
        granularity: Granularity,
    ) -> DataQualityTimeSeries:
        time_range, granularity = ensure_timeseries_parameters(
            info.context.model, time_range, granularity
        )
        return DataQualityTimeSeries(
            data=get_data_quality_timeseries_data(self.dimension, metric, time_range, granularity)
        )

    @strawberry.field(
        description=(
            "Returns the time series of the specified metric for data within a time range. Data"
            " points are generated starting at the end time and are separated by the sampling"
            " interval. Each data point is labeled by the end instant and contains data from their"
            " respective evaluation windows."
        )
    )  # type: ignore  # https://github.com/strawberry-graphql/strawberry/issues/1929
    def drift_time_series(
        self,
        info: Info[Context, None],
        metric: ScalarDriftMetric,
        time_range: TimeRange,
        granularity: Granularity,
    ) -> DriftTimeSeries:
        model = info.context.model
        if model[REFERENCE].empty:
            return DriftTimeSeries(data=[])
        time_range, granularity = ensure_timeseries_parameters(model, time_range, granularity)
        return DriftTimeSeries(
            data=get_drift_timeseries_data(self.dimension, metric, time_range, granularity)
        )


def to_gql_dimension(id_attr: int, dimension: ScalarDimension) -> Dimension:
    """
    Converts a phoenix.core.Dimension to a phoenix.server.api.types.Dimension
    """
    return Dimension(
        id_attr=id_attr,
        name=dimension.name,
        type=DimensionType.from_(dimension),
        dataType=DimensionDataType.from_(dimension),
        dimension=dimension,
    )
