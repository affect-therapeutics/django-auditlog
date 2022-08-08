import datetime
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HistoricalObjectState:
    log_found: bool
    """Boolean representing the presence of a log for the date given"""
    serialized_fields: Optional[dict] = None
    """Serialized fields from the data on the log entry or none if log not found"""
    timestamp: Optional[datetime.datetime] = None
    """Timestamp of the log for this state or none if log not found"""
    log_entry_id: Optional[int] = None
    """ID of the applicable LogEntry record"""

    @property
    def log_entry(self):
        from .models import LogEntry

        return LogEntry.objects.get(id=self.log_entry_id)


@dataclass
class HistoricalFieldState:
    log_found: bool
    """Boolean representing the presence of a log for the date given"""
    field_found: bool
    """Boolean representing the presence of a field in the serialized data."""
    field_name: str
    """Name of the field being referenced"""
    value: Optional[Any] = None
    """Value of the found field or none if not found"""
    timestamp: Optional[datetime.datetime] = None
    """Timestamp of the log for this state of the field value or none if not found"""
    log_entry_id: Optional[int] = None
    """ID of the applicable LogEntry record"""

    @property
    def log_entry(self):
        from .models import LogEntry

        return LogEntry.objects.get(id=self.log_entry_id)


class HistoricalStateLookupManagerMixin:
    def get_for_object(self, instance):
        raise NotImplementedError(f"{self.__class__} requires a get_for_object method.")

    def get_object_state_at_timestamp(self, instance, timestamp):
        """
        Get state of an instance at a given timestamp

        :param instance: The object subject to the historical search.
        :type instance: Model
        :param timestamp: The datetime representing the target of the historical search
        :type timestamp: Datetime
        :return: A dataclass object representing the results of the search
        :rtype: HistoricalObjectState
        """
        from .models import LogEntry

        log = (
            self.get_for_object(instance)
            .filter(timestamp__lte=timestamp)
            .order_by("-timestamp")
            .first()
        )

        # Exit if log not found for given timestamp
        if not isinstance(log, LogEntry):
            return HistoricalObjectState(log_found=False)

        # Otherwise, get the serialized fields or none
        if isinstance(log.serialized_data, dict):
            serialized_fields = log.serialized_data.get("fields", {}).copy() or None
        else:
            serialized_fields = None

        # Return a historical object state
        return HistoricalObjectState(
            log_found=True,
            serialized_fields=serialized_fields,
            timestamp=log.timestamp,
            log_entry_id=log.id,
        )

    def get_field_state_at_timestamp(self, instance, field_name, timestamp):
        """
        Get state of an instance's field at a given timestamp

        :param instance: The object subject to the historical search.
        :type instance: Model
        :param field_name: The name of the field to perform the historical search for
        :type field_name: str
        :param timestamp: The datetime representing the target of the historical search
        :type timestamp: Datetime
        :return: A dataclass object representing the results of the search
        :rtype: HistoricalFieldState
        """
        object_state = self.get_object_state_at_timestamp(instance, timestamp)

        kwargs = {"field_name": field_name}

        # Exit here if log not found for this timestamp
        if not object_state.log_found:
            return HistoricalFieldState(
                log_found=False,
                field_found=False,
                field_name=field_name,
            )

        kwargs.update(
            {
                "log_found": True,
                "timestamp": object_state.timestamp,
                "log_entry_id": object_state.log_entry_id,
            }
        )
        fields = object_state.serialized_fields

        # Exit if log found but there isn't serialized data or data does not
        # contain the given field
        if not isinstance(fields, dict) or field_name not in fields:
            return HistoricalFieldState(field_found=False, **kwargs)

        # Otherwise, provide the field value and return the field state object
        else:
            return HistoricalFieldState(
                field_found=True, value=fields.get(field_name), **kwargs
            )
