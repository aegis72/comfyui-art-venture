import time
import requests
import traceback
from typing import Callable

from .log import logger as log


def request_with_retry(
    make_request: Callable[[], requests.Response],
    max_try: int = 3,
    retries: int = 0,
):
    try:
        res = make_request()
        if res.status_code > 400:
            raise Exception(res.text)

        return True
    except requests.exceptions.ConnectionError:
        log.error("Connection error")
        if retries >= max_try - 1:
            return False

        time.sleep(2)
        log.info(f"Retrying {retries + 1}...")
        return request_with_retry(
            make_request,
            max_try=max_try,
            retries=retries + 1,
        )
    except Exception as e:
        log.error("Request error")
        log.error(e)
        log.debug(traceback.format_exc())
        return False


def get_dict_attribute(dict_inst: dict, name_string: str, default=None):
    nested_keys = name_string.split(".")
    value = dict_inst

    for key in nested_keys:
        value = value.get(key, None)

        if value is None:
            return default

    return value


def set_dict_attribute(dict_inst: dict, name_string: str, value):
    """
    Set an attribute to a dictionary using dot notation.
    If the attribute does not already exist, it will create a nested dictionary.

    Parameters:
        - dict_inst: the dictionary instance to set the attribute
        - name_string: the attribute name in dot notation (ex: 'attributes[1].name')
        - value: the value to set for the attribute

    Returns:
        None
    """
    # Split the attribute names by dot
    name_list = name_string.split(".")

    # Traverse the dictionary and create a nested dictionary if necessary
    current_dict = dict_inst
    for name in name_list[:-1]:
        is_array = name.endswith("]")
        if is_array:
            open_bracket_index = name.index("[")
            idx = int(name[open_bracket_index + 1 : -1])
            name = name[:open_bracket_index]

        if name not in current_dict:
            current_dict[name] = [] if is_array else {}

        current_dict = current_dict[name]
        if is_array:
            while len(current_dict) <= idx:
                current_dict.append({})
            current_dict = current_dict[idx]

    # Set the final attribute to its value
    name = name_list[-1]
    if name.endswith("]"):
        open_bracket_index = name.index("[")
        idx = int(name[open_bracket_index + 1 : -1])
        name = name[:open_bracket_index]

        if name not in current_dict:
            current_dict[name] = []

        while len(current_dict[name]) <= idx:
            current_dict[name].append(None)

        current_dict[name][idx] = value
    else:
        current_dict[name] = value