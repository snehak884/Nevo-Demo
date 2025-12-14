import importlib


def create_instance_from_string(class_path: str, *args, **kwargs):
    """
    Instantiates a class from a string.

    Args:
        class_path: A string specifying the full path to the class
                    (e.g., 'my_module.my_class').
        *args: Positional arguments to pass to the class constructor.
        **kwargs: Keyword arguments to pass to the class constructor.

    Returns:
        An instance of the specified class.
    """
    try:
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        instance = class_(*args, **kwargs)
        return instance
    except (ImportError, AttributeError, ValueError) as e:
        raise ValueError(f"Could not instantiate class {class_path}: {e}") from e
