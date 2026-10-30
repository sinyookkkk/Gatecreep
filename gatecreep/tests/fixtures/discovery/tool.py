"""Synthetic tool with two public actions and a dynamic extension boundary."""
import importlib

def format_result(value):
    return str(value)

def run(action, value):
    if action == 'show':
        return format_result(value)
    if action == 'count':
        return len(value)
    raise ValueError('unknown action')

def register(module_name):
    return importlib.import_module(module_name).tools
