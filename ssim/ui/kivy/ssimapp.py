"""Storage Sizing and Placement Kivy application"""
from contextlib import ExitStack
import itertools
import os
import re
import pandas as pd
from threading import Thread
import matplotlib.pyplot as plt
from typing import List

import numpy as np

from math import cos, hypot

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg


import opendssdirect as dssdirect
from importlib_resources import files, as_file

from ssim.metrics import ImprovementType, Metric, MetricTimeAccumulator

import kivy
import functools
from kivymd.app import MDApp
from ssim.ui import Project, StorageOptions, is_valid_opendss_name
from kivy.logger import Logger, LOG_LEVELS
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.list import IRightBodyTouch, ILeftBodyTouch, TwoLineAvatarIconListItem, OneLineAvatarIconListItem
from kivy.uix.boxlayout import BoxLayout
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.uix.behaviors import FocusBehavior
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDFlatButton, MDRectangleFlatIconButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.tab import MDTabsBase
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivymd.uix.tab import MDTabsBase

from kivymd.app import MDApp
from kivymd.uix.list import (
    TwoLineAvatarIconListItem,
    TwoLineIconListItem,
    ILeftBodyTouch,
    OneLineRightIconListItem,
    MDList
)

from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.textfield import MDTextField

import tomli
from kivymd.uix.label import MDLabel

from ssim.ui import (
    Configuration,
    Project,
    StorageOptions,
    ProjectResults,
    Results,
    is_valid_opendss_name
)


_FONT_FILES = {
    "exo_regular": "Exo2-Regular.ttf",
    "exo_bold": "Exo2-Bold.ttf",
    "exo_italic": "Exo2-Italic.ttf",
    "opensans_regular": "OpenSans-Regular.ttf",
    "opensans_bold": "OpenSans-Bold.ttf",
    "opensans_italic": "OpenSans-Italic.ttf"
}


_IMAGE_FILES = [
    "button_down.png", "button_normal.png", "gray.png", "white.png"
]


_KV_FILES = ["common.kv", "ssim.kv"]


def make_xy_grid_data(xs: list, ys: list) -> list:
    """A utility method to create a list of dictionaries suitable for use by an
    XYGrid.

    Parameters
    ----------
    xs : list
        The x value list to be the x values in the resulting dictionary.
    ys : list
        The y value list to be the y values in the resulting dictionary.

    Returns
    -------
    list:
        A list of dictionaries of the form
        [{x: x1, y: y1}, {x: x2, y: y2}, ..., {x: xn, y: yn}] which is what's required
        by an XY grid..
    """
    return [{'x': xs[i], 'y': ys[i]} for i in range(len(xs))]


def parse_float(strval) -> float:
    """A utility method to parse a string into a floating point value.

    This differs from a raw cast (float(strval)) in that it swallows
    exceptions.

    Parameters
    ----------
    strval
        The string to try and parse into a floating point number.

    Returns
    -------
    float:
        The value that resulted from parsing the supplied string to a float
        or None if the cast attempt caused an exception.
    """
    try:
        return float(strval)
    except ValueError:
        return None


def parse_float_or_str(strval):
    """A utility method to parse a string into a floating point value or
     leave it as is if the cast fails.

    This used parse_float and if that fails, this returns the supplied input string.

    Parameters
    ----------
    strval
        The string to try and parse into a floating point number.

    Returns
    -------
    float or str:
        This returns None if the supplied input string is None.  Otherwise, it
        tries to cast the input string to a float.   If that succeeds, then the
        float is returned.  If it doesn't, then the supplied string is returned
        unaltered.
    """
    if not strval: return None
    flt = parse_float(strval)
    return strval if flt is None else flt


def try_co_sort(xl: list, yl: list) -> (list, list):
    """Attempts to co-sort the supplied lists using the x-list as the sort index

    Parameters
    ----------
    xl : list
        The list of "x" values in this grid view to be sorted and treated as the index.
    yl: list
        The list of "y" values in this grid view to be sorted in accordance with the x-list.

    Returns
    -------
    tuple:
        If the two lists can be co-sorted, then the co-sorted versions of them will be
        returned.  If they cannot b/c an exception occurs, then they are returned
        unmodified.
    """
    if len(xl) < 2: return (xl, yl)

    try:
        return (list(t) for t in zip(*sorted(zip(xl, yl))))
    except:
        return (xl, yl)


class SSimApp(MDApp):

    def __init__(self, *args, **kwargs):
        self.project = Project("unnamed")
        super().__init__(*args, **kwargs)

    def build(self):

        screen_manager = ScreenManager()
        screen_manager.add_widget(SSimScreen(self.project, name="ssim"))
        screen_manager.add_widget(
            DERConfigurationScreen(self.project, name="der-config"))
        screen_manager.add_widget(
            LoadConfigurationScreen(self.project, name="load-config"))
        screen_manager.add_widget(
            MetricConfigurationScreen(self.project, name="metric-config"))
        screen_manager.add_widget(
            RunSimulationScreen(self.project, name="run-sim"))
        # screen_manager.add_widget(
        #     ResultsVisualizeScreen(self.project, name="results-visualize"))
        screen_manager.add_widget(
            ResultsSummaryScreen(self.project, name="results-summary"))
        screen_manager.add_widget(
            ResultsCompareScreen(self.project, name="results-compare"))
        screen_manager.add_widget(
            ResultsDetailScreen(self.project, name="results-detail"))
        screen_manager.current = "ssim"

        return screen_manager


class SSimBaseScreen(Screen):
    """Base class for screens that holds the fundamental ssim data structures.

    Attributes:
        project : :py:class:`ssim.ui.Project`

    Parameters
    ----------
    project : ssim.ui.Project
        Project object where the simulation configuration is being constructed.
    """

    def __init__(self, project, *args, **kwargs):
        self.project = project
        self.project_results = ProjectResults(self.project)
        super().__init__(*args, **kwargs)


class MatlabPlotBox(BoxLayout):

    def reset_plot(self):
        """Clears the current diagram widget and draws a new one using the current
            figure (plt.gcf())"""
        self.clear_widgets()
        self.add_widget(FigureCanvasKivyAgg(plt.gcf()))

    def display_plot_error(self, msg):
        """Puts a label with a supplied message in place of the diagram when there is a
            reason a diagram can't be displayed.

        Parameters
        ----------
        msg : str
            The message to show in place of the diagram when one can't be displayed.
        """
        self.clear_widgets()
        self.add_widget(MDLabel(text=msg))


class LeftCheckBox(ILeftBodyTouch, MDCheckbox):
    pass


class BusListItem(TwoLineIconListItem):

    def __init__(self, busname, busphases, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.text = busname
        self.secondary_text = str(busphases)

    def mark(self, check, the_list_item):
        """mark the task as complete or incomplete"""
        if check.active:
            self.parent.parent.parent.add_bus(the_list_item)
        else:
            self.parent.parent.parent.remove_bus(the_list_item)

    @property
    def active(self):
        return self.ids.selected.active


class TextFieldFloat(MDTextField):
    SIMPLE_FLOAT = re.compile(r"(\+|-)?\d*(\.\d*)?$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper_text_mode = "on_focus"
        self.helper_text = "Input value and press enter"

    def text_valid(self):
        return TextFieldFloat.SIMPLE_FLOAT.match(self.text) is not None

    def set_text(self, instance, value):
        if value == "":
            return
        self.set_error_message()

    def set_error_message(self):
        if not self.text_valid():
            self.error = True
            self.helper_text = "You must enter a number."
        else:
            self.error = False
            self.helper_text = "Input value and press enter"


class TextFieldMultiFloat(MDTextField):
    SIMPLE_FLOAT = re.compile(r"(\+|-)?\d*(\.\d*)?$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper_text_mode = "on_focus"
        self.helper_text = "Input numeric value"

    def text_valid(self):
        return TextFieldMultiFloat.SIMPLE_FLOAT.match(self.text) is not None

    def set_text(self, instance, value):
        if value == "":
            return
        self.set_error_message()

    def set_varied_mode(self):
        self.text = ""
        self.helper_text = "Multiple varied values"
        self.error = False

    def set_not_set_mode(self):
        self.text = ""
        self.helper_text = "No values set"
        self.error = False

    def set_error_message(self):
        if not self.text_valid():
            self.error = True
            self.helper_text = "You must enter a number."
        else:
            self.error = False
            self.helper_text = "Input numeric value"


class TextFieldPositiveFloat(MDTextField):

    POSITIVE_FLOAT = re.compile(r"((\d+(\.\d*)?)|(\d*(\.\d+)))$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper_text_mode = "on_focus"
        self.helper_text = "Input value and press enter"

    def text_valid(self):
        return TextFieldPositiveFloat.POSITIVE_FLOAT.match(self.text) is not None

    def set_text(self, instance, value):
        if value == "":
            return
        self.set_error_message()

    def set_error_message(self):
        if not self.text_valid():
            self.error = True
            self.helper_text = "You must enter a non-negative number."
        else:
            self.error = False
            self.helper_text = "Input value and press enter"


class StorageControlModelTab(FloatLayout, MDTabsBase):
    pass


class TextFieldPositivePercentage(MDTextField):
    POSITIVE_FLOAT = re.compile(r"\d*(\.\d*)?$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper_text_mode = "on_focus"
        self.helper_text = "Input percentage value (0-100)"

    def text_valid(self):
        if TextFieldPositivePercentage.POSITIVE_FLOAT.match(self.text) is None:
            return False

        value = float(self.text)
        if value < 0.0: return False
        if value > 100: return False
        return True

    def set_text(self, instance, value):
        if value == "":
            return
        self.set_error_message()

    def set_error_message(self):
        if not self.text_valid():
            self.error = True
            self.helper_text = "You must enter a value between 0 and 100."
        else:
            self.error = False
            self.helper_text = "Input percentage value"

    def percentage(self):
        return float(self.text)

    def fraction(self):
        return self.percentage() / 100.0


class EditableSetList(MDList):
    options = ObjectProperty(set())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind(
            options=self._update_display
        )

    def _update_display(self, instance, options):
        self.clear_widgets()
        for item in sorted(options):
            self.add_widget(
                EditableSetListItem(item, text=str(item))
            )

    def add_item(self, item):
        """Add an item to the set."""
        self.options = self.options.union(set([item]))

    def remove_item(self, item):
        """Remove an item from the set."""
        # Don't use set.remove() since we must return a new object
        # to trigger the _update_display callback throug kivy
        self.options = self.options - set([item])


class EditableSetListItem(OneLineRightIconListItem):
    """List item with one line and a delete button"""

    def __init__(self, item, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = item
        self.ids.delete.bind(on_release=self._delete_item)

    def _delete_item(self, item):
        self.parent.remove_item(self._value)


class TextFieldOpenDSSName(MDTextField):
    """Text field that enforces OpenDSS name requirements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def text_valid(self):
        return is_valid_opendss_name(self.text)

    def set_text(self, instance, value):
        if value == "":
            self.error = True
        else:
            self.set_error_message()

    def set_error_message(self):
        if not self.text_valid():
            self.error = True
        else:
            self.error = False


class StorageConfigurationScreen(SSimBaseScreen):
    """Configure a single energy storage device."""

    def __init__(self, der_screen, ess: StorageOptions, *args, **kwargs):
        super().__init__(der_screen.project, *args, **kwargs)
        self._der_screen = der_screen
        self.ids.power_input.bind(
            on_text_validate=self._add_device_power
        )
        self.ids.duration_input.bind(
            on_text_validate=self._add_device_duration
        )
        self.ids.device_name.bind(
            on_text_validate=self._check_name
        )
        self.options = ess
        self.initialize_widgets()

    def initialize_widgets(self):
        if self.options is None: return

        for power in self.options.power:
            self.ids.power_list.add_item(power)

        for duration in self.options.duration:
            self.ids.duration_list.add_item(duration)

        self.ids.device_name.text = self.options.name

        for bus_list_item in self.ids.bus_list.children:
            if bus_list_item.text in self.options.busses:
                bus_list_item.ids.selected.active = True

        self.ids.required.active = self.options.required

        Clock.schedule_once(lambda dt: self._refocus_field(self.ids.device_name), 0.05)

    def on_kv_post(self, base_widget):
        self.ids.bus_list.clear_widgets()
        for bus in self.project.bus_names:
            bus_list_item = BusListItem(bus, self.project.phases(bus))
            self.ids.bus_list.add_widget(bus_list_item)

    def _check_name(self, textfield):
        if not textfield.text_valid():
            textfield.helper_text = "invalid name"
            textfield.error = True
            return False
        existing_names = {name.lower() for name in self.project.storage_names}
        if textfield.text.lower() in existing_names:
            textfield.helper_text = "Name already exists"
            textfield.error = True
            return False
        textfield.error = False
        return True

    def _add_option(self, optionlist, textfield):
        if textfield.text_valid():
            value = float(textfield.text)
            optionlist.add_item(value)
            textfield.text = ""
            Clock.schedule_once(lambda dt: self._refocus_field(textfield), 0.05)
        else:
            textfield.set_error_message()

    def _refocus_field(self, textfield):
        textfield.focus = True

    def _add_device_duration(self, textfield):
        self._add_option(self.ids.duration_list, textfield)

    def _add_device_power(self, textfield):
        self._add_option(self.ids.power_list, textfield)

    @property
    def _ess_powers(self):
        return list(self.ids.power_list.options)

    @property
    def _ess_durations(self):
        return list(self.ids.duration_list.options)

    @property
    def _selected_busses(self):
        return list(
            bus_item.text
            for bus_item in self.ids.bus_list.children
            if bus_item.active
        )

    def edit_control_params(self):
        self._record_option_data()

        self.manager.add_widget(
            StorageControlConfigurationScreen(
                self, self.project, self.options, name="configure-storage-controls"
            )
        )

        self.manager.current = "configure-storage-controls"

    def _record_option_data(self) -> StorageOptions:

        if self.options:
            self.options.power = self._ess_powers
            self.options.duration = self._ess_durations
            self.options.busses = self._selected_busses
            self.options.required = self.ids.required.active
            self.options.name = self.ids.device_name.text
            self.options.phases = 3
        else:
            self.options = StorageOptions(
                self.ids.device_name.text,
                3,
                self._ess_powers,
                self._ess_durations,
                self._selected_busses,
                required=self.ids.required.active
            )

    def __show_invalid_input_values_popup(self, msg):
        content = MessagePopupContent()

        popup = Popup(
            title='Invalid Storage Input', content=content, auto_dismiss=False,
            size_hint=(0.4, 0.4)
            )
        content.ids.msg_label.text = str(msg)
        content.ids.dismissBtn.bind(on_press=popup.dismiss)
        popup.open()
        return

    def show_error(self, msg):
        if msg:
            self.__show_invalid_input_values_popup(msg)
            return True

        return False

    def save(self):
        self._record_option_data()

        if not self.options.valid:
            Logger.error(
                "invalid storage configuration - "
                f"name: {self.options.name}, "
                f"powers: {self.options.power}, "
                f"durations: {self.options.duration}, "
                f"busses: {self.options.busses}"
            )

        if self.show_error(self.options.validate_name()): return
        if self.show_error(self.options.validate_soc_values()): return
        if self.show_error(self.options.validate_power_values()):  return
        if self.show_error(self.options.validate_duration_values()): return
        if self.show_error(self.options.validate_busses()): return
        if self.show_error(self.options.validate_controls()): return

        #self._der_screen.add_ess(self.options)
        self.manager.current = "der-config"
        self.manager.remove_widget(self)

    def cancel(self):
        #if self._editing is not None:
            # Restore the original device
        #    self._der_screen.add_ess(self._editing)
        self.manager.current = "der-config"
        self.manager.remove_widget(self)

    def on_enter(self, *args):
        return super().on_enter(*args)


class XYGridView(RecycleView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type("on_item_deleted")
        self.register_event_type("on_value_changed")

    def delete_item(self, index: int):
        self.data.pop(index)
        Clock.schedule_once(lambda dt: self.__raise_value_changed(), 0.05)

    def x_value_changed(self, index: int, value):
        self.__on_value_changed(index, "x", value)

    def y_value_changed(self, index: int, value):
        self.__on_value_changed(index, "y", value)

    def __on_value_changed(self, index:int, key: str, value):
        self.data[index][key] = parse_float_or_str(value)
        Clock.schedule_once(lambda dt: self.__raise_value_changed(), 0.05)

    def __raise_value_changed(self):
        self.dispatch("on_value_changed")

    def on_value_changed(self):
        pass

    def on_item_deleted(self):
        pass

    def __on_deleted_item(self):
        self.dispatch("on_item_deleted")

    def extract_data_lists(self, sorted: bool = True) -> (list, list):
        """Reads all values out of the "x" and "y" columns of this control and returns them as
            pair of lists that may be sorted if requested.

        Parameters
        ----------
        sorted : bool
            True if this method should try and c0-sort the extracted x and y lists before
            returning them and false otherwise.

        Returns
        -------
        tuple:
            A pair of lists containing the x and y values in this grid.  The lists will be
            co-sorted using the x list as an index if requested and they can be sorted.
        """
        xvs = self.extract_x_vals()
        yvs = self.extract_y_vals()
        if not sorted: return (xvs, yvs)
        return try_co_sort(xvs, yvs)

    def extract_x_vals(self) -> list:
        """Reads all values out of the "x" column of this control and returns them as a list.

        Returns
        -------
        list:
            A list containing all values in the "x" column of this control.  The values in
            the list will be of type float if they can be cast as such.  Otherwise, raw text
            representations will be put in the list in locations where the cast fails.
        """
        return [child.x_value for child in self.children[0].children]

    def extract_y_vals(self) -> list:
        """Reads all values out of the "y" column of this control and returns them as a list.

        Returns
        -------
        list:
            A list containing all values in the "y" column of this control.  The values in
            the list will be of type float if they can be cast as such.  Otherwise, raw text
            representations will be put in the list in locations where the cast fails.
        """
        return [child.y_value for child in self.children[0].children]


class XYGridViewItem(RecycleDataViewBehavior, BoxLayout):

    index: int = -1

    last_text: str = ""

    @property
    def x_value(self):
        """Returns the current contents of the x value field of this row.

        Returns
        -------
        float or str:
            If the current content of the x value field of this row can be cast to
            a float, then the float is returned.  Otherwise, the raw string contents
            of the field are returned.
        """
        return parse_float_or_str(self.ids.x_field.text)

    @property
    def y_value(self):
        """Returns the current contents of the y value field of this row.

        Returns
        -------
        float or str:
            If the current content of the y value field of this row can be cast to
            a float, then the float is returned.  Otherwise, the raw string contents
            of the field are returned.
        """
        return parse_float_or_str(self.ids.y_field.text)

    def refresh_view_attrs(self, rv, index, data):
        """A method of the RecycleView called automatically to refresh the content of the view.

        Parameters
        ----------
        rv : RecycleView
            The RecycleView that owns this row and wants it refreshed (not used in this function).
        index: int
            The index of this row.
        data: dict
            The dictionary of data that constitutes this row.  Should have keys for 'x' and 'y'.
        """
        self.index = index
        self.ids.x_field.text = str(data['x'])
        self.ids.y_field.text = str(data['y'])

    def on_delete_button(self):
        """A callback function for the button that deletes the data item represented by
        this row from the data list"""
        self.parent.parent.delete_item(self.index)

    def on_x_value_changed(self, instance, text):
        """A callback method used when the value in the x field of an XY grid changes.

        This method notifies the grandparent, which is an XYGridView, of the change.

        Parameters
        ----------
        instance
            The x text field whose value has changed.
        text
            The new x value as a string.
        """
        if self.parent:
            self.parent.parent.x_value_changed(self.index, self.x_value)

    def on_x_focus_changed(self, instance, value):
        """A callback method used when the focus on the x field of an XY grid changes.

        This method checks to see if this is a focus event or an unfocus event.
        If focus, it stores the current value in the field for comparison later.
        If unfocus and the value has not changed, nothing is done.  If the value has changed,
        then the self.on_x_value_changed method is invoked.

        Parameters
        ----------
        instance
            The x text field whose value has changed.
        value
            True if this is a focus event and false if it is unfocus.
        """
        if value:
            self.last_text = instance.text
        elif value != instance.text:
            self.on_x_value_changed(instance, instance.text)

    def on_y_value_changed(self, instance, text):
        """A callback method used when the value in the y field of an XY grid is validated.

        This method notifies the grandparent, which is an XYGridView, of the change.

        Parameters
        ----------
        instance
            The y text field whose value has changed.
        text
            The new y value as a string.
        """
        if self.parent:
            self.parent.parent.y_value_changed(self.index, self.y_value)

    def on_y_focus_changed(self, instance, value):
        """A callback method used when the focus on the y field of an XY grid changes.

        This method checks to see if this is a focus event or an unfocus event.
        If focus, it stores the current value in the field for comparison later.
        If unfocus and the value has not changed, nothing is done.  If the value has changed,
        then the self.on_y_value_changed method is invoked.

        Parameters
        ----------
        instance
            The y text field whose value has changed.
        value
            True if this is a focus event and false if it is unfocus.
        """
        if value:
            self.last_text = instance.text
        elif value != instance.text:
            self.on_y_value_changed(instance, instance.text)


class XYItemTextField(TextInput):
    """A class to serve as a text field used in an XY grid.

    This class can be either an x or a y value field and enforces the
    requirement that the contents be a floating point number by indicating
    if it is not.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.def_back_color = self.background_color
        self.bind(text = self.set_error_message)
        self.hint_text = "Enter a number."

    def set_error_message(self, instance, text):
        """A function to set this text field to an error state.

        This method checks to see if the contents of this text field are
        a floating point number and does nothing if so.  If not, then this
        sets the background color to "red".
        """
        v = parse_float(text) is not None
        self.background_color = "red" if not v else self.def_back_color


class VoltVarTabContent(BoxLayout):
    """The class that stores the content for the Volt-Var tab in the storage
     option control tabs"""

    def on_add_button(self):
        """A callback function for the button that adds a new value to the volt-var grid"""
        self.ids.grid.data.append({'x': 1.0, 'y': 1.0})
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_sort_button(self):
        """A callback function for the button that sorts the volt-var grid by voltage"""
        xs, ys = self.ids.grid.extract_data_lists()
        self.ids.grid.data = make_xy_grid_data(xs, ys)

    def on_reset_button(self):
        """A callback function for the button that resets the volt-var grid data to defaults"""
        xs = [0.5, 0.95, 1.0, 1.05, 1.5]
        ys = [1.0, 1.0, 0.0, -1.0, -1.0]
        self.ids.grid.data = make_xy_grid_data(xs, ys)
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def rebuild_plot(self):
        """A function to reset the plot of the volt var data.

        This method extracts the volt var data out of the UI grid and then, if
        the data exists, plots it in the associated plot.
        """
        xs, ys = self.ids.grid.extract_data_lists()

        if len(xs) == 0:
            self.ids.plot_box.display_plot_error("No Data")

        else:
            _make_xy_matlab_plot(
                self.ids.plot_box, xs, ys, 'Voltage (p.u.)',
                'Reactive Power (p.u.)', 'Volt-Var Control Parameters'
            )


class VoltWattTabContent(BoxLayout):
    """The class that stores the content for the Volt-Watt tab in the storage
     option control tabs"""

    def on_add_button(self):
        """A callback function for the button that adds a new value to the volt-watt grid"""
        self.ids.grid.data.append({'x': 1.0, 'y': 1.0})
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_sort_button(self):
        """A callback function for the button that sorts the volt-watt grid by voltage"""
        xs, ys = self.ids.grid.extract_data_lists()
        self.ids.grid.data = make_xy_grid_data(xs, ys)

    def on_reset_button(self):
        """A callback function for the button that resets the volt-var grid data to defaults"""
        xs = [0.5, 0.95, 1.0, 1.05, 1.5]
        ys = [1.0, 1.0, 0.0, -1.0, -1.0]
        self.ids.grid.data = make_xy_grid_data(xs, ys)
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def rebuild_plot(self):
        """A function to reset the plot of the volt watt data.

        This method extracts the volt watt data out of the UI grid and then, if
        the data exists, plots it in the associated plot.
        """
        xs, ys = self.ids.grid.extract_data_lists()

        if len(xs) == 0:
            self.ids.plot_box.display_plot_error("No Data")

        else:
            _make_xy_matlab_plot(
                self.ids.plot_box, xs, ys, 'Voltage (p.u.)',
                'Watts (p.u.)', 'Volt-Watt Control Parameters'
            )


class VarWattTabContent(BoxLayout):
    """The class that stores the content for the Var-Watt tab in the storage
     option control tabs"""

    def on_add_button(self):
        """A callback function for the button that adds a new value to the var-watt grid"""
        self.ids.grid.data.append({'x': 1.0, 'y': 1.0})
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_sort_button(self):
        """A callback function for the button that sorts the var-watt grid by reactive power"""
        xs, ys = self.ids.grid.extract_data_lists()
        self.ids.grid.data = make_xy_grid_data(xs, ys)

    def on_reset_button(self):
        """A callback function for the button that resets the volt-var grid data to defaults"""
        xs = [0.5, 0.95, 1.0, 1.05, 1.5]
        ys = [1.0, 1.0, 0.0, -1.0, -1.0]
        self.ids.grid.data = make_xy_grid_data(xs, ys)
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def rebuild_plot(self):
        """A function to reset the plot of the var watt data.

        This method extracts the var watt data out of the UI grid and then, if
        the data exists, plots it in the associated plot.
        """
        xs, ys = self.ids.grid.extract_data_lists()

        if len(xs) == 0:
            self.ids.plot_box.display_plot_error("No Data")

        else:
            _make_xy_matlab_plot(
                self.ids.plot_box, xs, ys, 'Reactive Power (p.u.)',
                'Watts (p.u.)', 'Var-Watt Control Parameters'
            )


class VoltVarVoltWattTabContent(BoxLayout):
    """The class that stores the content for the Volt-Var & Volt-Watt tab in the storage
     option control tabs"""

    def on_add_vv_button(self):
        """A callback function for the button that adds a new value to the volt-var grid"""
        self.ids.vv_grid.data.append({'x': 1.0, 'y': 1.0})
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_add_vw_button(self):
        """A callback function for the button that adds a new value to the volt-watt grid"""
        self.ids.vw_grid.data.append({'x': 1.0, 'y': 1.0})
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_reset_vv_button(self):
        """A callback function for the button that resets the volt-var grid data to defaults"""
        xs = [0.5, 0.95, 1.0, 1.05, 1.5]
        ys = [1.0, 1.0, 0.0, -1.0, -1.0]
        self.ids.vv_grid.data = make_xy_grid_data(xs, ys)
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_reset_vw_button(self):
        """A callback function for the button that resets the volt-var grid data to defaults"""
        xs = [0.5, 0.95, 1.0, 1.05, 1.5]
        ys = [1.0, 1.0, 0.0, -1.0, -1.0]
        self.ids.vw_grid.data = make_xy_grid_data(xs, ys)
        Clock.schedule_once(lambda dt: self.rebuild_plot(), 0.05)

    def on_sort_vv_button(self):
        """A callback function for the button that sorts the volt-var grid by voltage"""
        xs, ys = self.ids.vv_grid.extract_data_lists()
        self.ids.vv_grid.data = make_xy_grid_data(xs, ys)

    def on_sort_vw_button(self):
        """A callback function for the button that sorts the volt-watt grid by voltage"""
        xs, ys = self.ids.vw_grid.extract_data_lists()
        self.ids.vw_grid.data = make_xy_grid_data(xs, ys)

    def rebuild_plot(self):
        """A function to reset the plot of the volt var and volt watt data.

        This method extracts the volt var and volt watt data out of the UI grids and then, if
        the data exists, plots them in the associated plot, 1 on each of two y axes.
        """
        vxs, vys = self.ids.vv_grid.extract_data_lists()
        wxs, wys = self.ids.vw_grid.extract_data_lists()

        if len(vxs) == 0 and len(wxs) == 0:
            self.ids.plot_box.display_plot_error("No Data")

        else:
            fig, ax1 = plt.subplots(1, 1, layout="constrained")
            l1, = ax1.plot(vxs, vys, marker='o')
            ax1.set_xlabel('Voltage (p.u.)')
            ax1.set_ylabel('Reactive Power (p.u.)')

            ax2 = ax1.twinx()
            l2, = ax2.plot(wxs, wys, color="red", marker='o')
            ax2.set_ylabel('Watts (p.u.)', color="red")
            ax2.tick_params(axis='y', labelcolor="red")

            ax1.legend([l1, l2], ["Volt-Var", "Volt-Watt"])
            plt.title('Volt-Var & Volt-Watt Control Parameters')
            self.ids.plot_box.reset_plot()


class StorageControlConfigurationScreen(SSimBaseScreen):
    """Configure the control strategy of a single energy storage device."""

    def __init__(self, der_screen, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._der_screen = der_screen
        self._options = args[0]

        self.ids.min_soc.text = str(self._options.min_soc*100.0)
        self.ids.max_soc.text = str(self._options.max_soc*100.0)
        self.ids.init_soc.text = str(self._options.initial_soc*100.0)

        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(self.ids.max_soc), 0.05)
        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(self.ids.min_soc), 0.05)
        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(self.ids.init_soc), 0.05)

        self.load_all_control_data()

        if self._options is not None:
            if self._options.control.mode == "droop":
                self.set_droop_mode()
            elif self._options.control.mode == "voltvar":
                self.set_volt_var_mode()
            elif self._options.control.mode == "voltwatt":
                self.set_volt_watt_mode()
            elif self._options.control.mode == "varwatt":
                self.set_var_watt_mode()
            elif self._options.control.mode == "vv_vw":
                self.set_volt_var_and_volt_watt_mode()
            elif self._options.control.mode == "constantpf":
                self.set_const_power_factor_mode()
            else:
                self.set_droop_mode()

    def load_all_control_data(self):
        """Verifies the existence of all control mode parameters and then sets the
        contents of the controls used to display and modify them.

        This uses the individual "set...data" methods for each control mode.  See those
        methods for more details of each.
        """
        self.set_droop_data()
        self.set_volt_var_data()
        self.set_volt_watt_data()
        self.set_var_watt_data()
        self.set_volt_var_and_volt_watt_data()
        self.set_const_power_factor_data()

    @staticmethod
    def __set_focus_clear_sel(widget, value = True):
        widget.focus = value
        Clock.schedule_once(lambda dt: widget.cancel_selection(), 0.05)

    def set_mode_label_text(self):
        """ Adds the current device name to the label that informs a user to select
        a current control model."""
        self.ids.mode_label.text =\
            f"Select a control mode for this storage asset: [b]{self.device_name}[/b]"

    @property
    def device_name(self) -> str:
        """Returns the name given to this storage device configuration or
        an empty string if none has been provided.

        Returns
        -------
        str:
            The name given to this storage option or an empty string if one has
            not been given.  This will not return None.
        """
        return "" if self._options is None else self._options.name

    def on_tab_switch(self, instance_tabs, instance_tab, instance_tab_label, tab_text):
        self.read_all_data()
        if tab_text == "Droop":
            self.set_droop_mode()
        elif tab_text == "Volt-Var":
            self.set_volt_var_mode()
        elif tab_text == "Volt-Watt":
            self.set_volt_watt_mode()
        elif tab_text == "Var-Watt":
            self.set_var_watt_mode()
        elif tab_text == "Volt-Var & Volt-Watt":
            self.set_volt_var_and_volt_watt_mode()
        elif tab_text == "Constant Power Factor":
            self.set_const_power_factor_mode()
        else:
            self.set_droop_mode()

    def set_droop_mode(self):
        """Changes the current contorl mode for the current storage option to droop.

        This ensures control parameters for the droop mode, registers the fields for data
        extraction, and sets focus on the two fields to put them into editing mode.
        """
        self.set_mode("droop", self.ids.droop_tab)
        self.set_droop_data()

    def set_droop_data(self):
        """Verifies the existence of droop parameters and then sets the contents of
        the controls used to display and modify them."""
        pval, qval = self.verify_droop_params()
        pfield = self.ids.droop_tab_content.ids.p_value
        qfield = self.ids.droop_tab_content.ids.q_value

        pfield.text = str(pval)
        qfield.text = str(qval)

        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(pfield), 0.05)
        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(qfield), 0.05)

    def verify_droop_params(self) -> (float, float):
        """ Checks to see if there is a recorded set of droop parameters in the current
        control parameters list and installs them as default values if they are missing.

        Default P is 500, and default Q is -300.

        Returns
        -------
        tuple:
            The result of verifying the P and Q droop parameters.
        """
        return (
            self.__verify_control_param("droop", "p_droop", 500),
            self.__verify_control_param("droop", "q_droop", -300)
            )

    def set_volt_var_mode(self):
        """Changes the current contorl mode for the current storage option to volt-var.

        This ensures control parameters for the volt-var mode and loads the volt-var
        data into the xy grid.
        """
        self.set_mode("voltvar", self.ids.vv_tab)
        self.set_volt_var_data()

    def set_volt_var_data(self):
        """Verifies the existence of Volt-Var parameters and then sets the contents of
        the controls used to display and modify them."""
        vvs, var = self.verify_volt_var_params()
        self.__set_xy_grid_data(self.ids.vv_tab_content.ids.grid, vvs, var)
        self.ids.vv_tab_content.rebuild_plot()

    def verify_volt_var_params(self) -> (list, list):
        """ Checks to see if there is a recorded set of Volt-Var parameters in the current
        control parameters list and installs them as default values if they are missing.

        Default volts are [0.5, 0.95, 1.0, 1.05, 1.5] and default VARs are
        [1.0, 1.0, 0.0, -1.0, -1.0].

        Returns
        -------
        tuple:
            The result of verifying the volt and var lists in the control parameters.
            The first member of the tuple will be the volts list and the second is the
            list of var values.
        """
        return (
            self.__verify_control_param("voltvar", "volts", [0.5, 0.95, 1.0, 1.05, 1.5]),
            self.__verify_control_param("voltvar", "vars", [1.0, 1.0, 0.0, -1.0, -1.0])
            )

    def set_volt_watt_mode(self):
        """Changes the current contorl mode for the current storage option to volt-watt.

        This ensures control parameters for the volt-var mode and loads the volt-watt
        data into the xy grid.
        """
        self.set_mode("voltwatt", self.ids.vw_tab)
        self.set_volt_watt_data()

    def set_volt_watt_data(self):
        """Verifies the existence of Volt-Watt parameters and then sets the contents of
        the controls used to display and modify them."""
        vvs, wvs = self.verify_volt_watt_params()
        self.__set_xy_grid_data(self.ids.vw_tab_content.ids.grid, vvs, wvs)
        self.ids.vw_tab_content.rebuild_plot()

    def verify_volt_watt_params(self) -> (list, list):
        """ Checks to see if there is a recorded set of Volt-Watt parameters in the current
        control parameters list and installs them as default values if they are missing.

        Default volts are [0.5, 0.95, 1.0, 1.05, 1.5] and default watts are
        [1.0, 1.0, 0.0, -1.0, -1.0].

        Returns
        -------
        tuple:
            The result of verifying the volt and watt lists in the control parameters.
            The first member of the tuple will be the volts list and the second is the
            list of watt values.
        """
        return (
            self.__verify_control_param("voltwatt", "volts", [0.5, 0.95, 1.0, 1.05, 1.5]),
            self.__verify_control_param("voltwatt", "watts", [1.0, 1.0, 0.0, -1.0, -1.0])
            )

    def set_var_watt_mode(self):
        """Changes the current contorl mode for the current storage option to var-watt.

        This ensures control parameters for the volt-var mode and loads the var-watt
        data into the xy grid.
        """
        self.set_mode("varwatt", self.ids.var_watt_tab)
        self.set_var_watt_data()

    def set_var_watt_data(self):
        """Verifies the existence of Var-Watt parameters and then sets the contents of
        the controls used to display and modify them."""
        vvs, wvs = self.verify_var_watt_params()
        self.__set_xy_grid_data(self.ids.var_watt_tab_content.ids.grid, vvs, wvs)
        self.ids.var_watt_tab_content.rebuild_plot()

    def verify_var_watt_params(self) -> (list, list):
        """ Checks to see if there is a recorded set of Var-Watt parameters in the current
        control parameters list and installs them as default values if they are missing.

        Default VARs are [0.5, 0.95, 1.0, 1.05, 1.5] and default Watts are
        [1.0, 1.0, 0.0, -1.0, -1.0].

        Returns
        -------
        tuple:
            The result of verifying the VAR and Watt lists in the control parameters.
            The first member of the tuple will be the VARs list and the second is the
            list of Watt values.
        """
        return (
            self.__verify_control_param("varwatt", "vars", [0.5, 0.95, 1.0, 1.05, 1.5]),
            self.__verify_control_param("varwatt", "watts", [1.0, 1.0, 0.0, -1.0, -1.0])
            )

    def set_volt_var_and_volt_watt_mode(self):
        """Changes the current contorl mode for the current storage option to volt-var &
            var-watt.

        This ensures control parameters for the volt-var mode and loads the volt-var &
        var-watt data into the xy grid.
        """
        self.set_mode("vv_vw", self.ids.vv_vw_tab)
        self.set_volt_var_and_volt_watt_data()

    def set_volt_var_and_volt_watt_data(self):
        """Verifies the existence of Volt-Var & Volt-Watt parameters and then sets the contents of
        the controls used to display and modify them."""
        vvvs, vars, vwvs, watts = self.verify_volt_var_and_volt_watt_params()
        self.__set_xy_grid_data(self.ids.vv_vw_tab_content.ids.vv_grid, vvvs, vars)
        self.__set_xy_grid_data(self.ids.vv_vw_tab_content.ids.vw_grid, vwvs, watts)
        self.ids.vv_vw_tab_content.rebuild_plot()

    def verify_volt_var_and_volt_watt_params(self) -> (list, list, list, list):
        """ Checks to see if there is a recorded set of Volt-Var and Volt_Watt parameters
        in the current control parameters list and installs them as default values if they
        are missing.

        Default Volts for Volt-Var are [0.5, 0.95, 1.0, 1.05, 1.5], default VARs for
        Volt-Var are [1.0, 1.0, 0.0, -1.0, -1.0], default Volts for Volt-Watt are
        [0.5, 0.95, 1.0, 1.05, 1.5], and default Watts for Volt-Watt are
        [1.0, 1.0, 0.0, -1.0, -1.0].

        Returns
        -------
        tuple:
            The result of verifying the Volt-Var and Volt-Watt lists in the control parameters.
            The first member of the tuple will be the Volt-Var Volts.  The second is the
            list of Volt-Var Var values.  The third is the list of Volt-Watt Volt values and
            finally, the fourth is the list of Watt Values of the Volt-Watt mode.
        """
        return (
            self.__verify_control_param("vv_vw", "vv_volts", [0.5, 0.95, 1.0, 1.05, 1.5]),
            self.__verify_control_param("vv_vw", "vv_vars", [1.0, 1.0, 0.0, -1.0, -1.0]),
            self.__verify_control_param("vv_vw", "vw_volts", [0.5, 0.95, 1.0, 1.05, 1.5]),
            self.__verify_control_param("vv_vw", "vw_watts", [1.0, 1.0, 0.0, -1.0, -1.0])
            )

    def set_const_power_factor_mode(self):
        """Changes the current contorl mode for the current storage option to const PF.

        This ensures control parameters for the const PF mode, registers the fields for data
        extraction, and sets focus on the two fields to put them into editing mode.
        """
        self.set_mode("constantpf", self.ids.const_pf_tab)
        self.set_const_power_factor_data()

    def set_const_power_factor_data(self):
        """Verifies the existence of the Constant Power Factor parameters and then sets the
        contents of the controls used to display and modify them."""
        cpf = self.verify_const_pf_params()
        pffield = self.ids.const_pf_tab_content.ids.pf_value
        pffield.text = str(cpf)
        Clock.schedule_once(lambda dt: self.__set_focus_clear_sel(pffield), 0.05)

    def verify_const_pf_params(self) -> float:
        """ Checks to see if there is a recorded constant power factor parameter in the current
        control parameters list and installs it as the default value if it is missing.

        Default PF is 0.99.

        Returns
        -------
        float:
            The result of verifying the constant PF value parameter.
        """
        return self.__verify_control_param("constantpf", "pf_val", 0.99)

    def __verify_control_param(self, mode: str, label: str, def_val):
        """Verifies that there is a data value in the control parameters for the current
        storage element and puts the default value in if not.

        Parameters
        ----------
        mode : str
            The control mode for which to store the default value for label
        label : str
            The key to check for in the current storage control parameters.
        def_val
            The value to put into the storage control parameters if a value is not found
            using the supplied label (key).
        """
        if mode not in self._options.control.params:
            self._options.control.params[mode] = {}

        if label not in self._options.control.params[mode]:
            self._options.control.params[mode][label] = def_val

        return self._options.control.params[mode][label]

    def __set_xy_grid_data(self, grid: XYGridView, xdat: list, ydat: list) -> list:
        """Converts the supplied lists into a dictionary appropriately keyed to be assigned
        as the data for the supplied grid and assignes it.

        This performs a try-co-sort of the lists prior to assignment to the grid data.

        Parameters
        ----------
        grid : XYGridView
            The grid to assign data to.
        xdat : list
            The list of x values to assign to the x column of the grid.
        ydat : list
            The list of y values to assign to the y column of the grid.

        Return
        ------
        list:
            The list of dictionaries that was craeted from the xdat and ydat. See the
            make_xy_grid_data function documentation for more details on the format of
            the returned list.
        """
        xs, ys = try_co_sort(xdat, ydat)
        grid.data = make_xy_grid_data(xs, ys)
        return grid.data

    def set_mode(self, name: str, tab) -> bool:
        """Changes the current contorl mode for the current storage option to the supplied
        one and sets the current tab.

        If the current control mode is the supplied one, then the only thing this does
        is set the supplied tab if it is not correct.

        Parameters
        ----------
        name : str
            The name of the control mode to make current.
        tab
            The tab page to make visible.

        Returns
        -------
        bool:
            True if this method goes so far as to actually change the mode and False if the
            the mode is already the requested one.  Regardless, this method will set the
            current tab if needed.
        """
        if self.ids.control_tabs.get_current_tab() is not tab:
            self.ids.control_tabs.switch_tab(tab.tab_label_text)

        if self._options.control.mode == name: return False
        self._options.control.mode = name
        #self._options.control.params.clear()
        return True

    def save(self):
        self.cancel()

    def read_all_data(self):
        """Reads all entered data out of the controls for all control modes.

        This uses the individual "read...data" methods for each mode.  See them for
        more information about each.
        """
        self._options.min_soc = self.ids.min_soc.fraction()
        self._options.max_soc = self.ids.max_soc.fraction()
        self._options.initial_soc = self.ids.init_soc.fraction()
        self.read_droop_data()
        self.read_const_pf_data()
        self.read_voltvar_data()
        self.read_voltwatt_data()
        self.read_varwatt_data()
        self.read_voltvar_and_voltwatt_data()

    def read_droop_data(self):
        """Reads and stores the entered data out of the controls for droop mode.

        The data is stored in the options control parameters.
        """
        droop_map = self._options.control.params["droop"]
        droop_map["p_droop"] = parse_float(self.ids.droop_tab_content.ids.p_value.text)
        droop_map["q_droop"] = parse_float(self.ids.droop_tab_content.ids.q_value.text)

    def read_const_pf_data(self):
        """Reads and stores the entered data out of the controls for constant power factor mode.

        The data is stored in the options control parameters.
        """
        constpf_map = self._options.control.params["constantpf"]
        constpf_map["pf_val"] = parse_float(self.ids.const_pf_tab_content.ids.pf_value.text)

    def read_voltvar_data(self):
        """Reads and stores the entered data out of the controls for Volt-Var mode.

        The data is stored in the options control parameters.
        """
        self._extract_and_store_data_lists(
            self.ids.vv_tab_content.ids.grid, "voltvar", "volts", "vars"
            )

    def read_voltwatt_data(self):
        """Reads and stores the entered data out of the controls for Volt-Watt mode.

        The data is stored in the options control parameters.
        """
        self._extract_and_store_data_lists(
            self.ids.vw_tab_content.ids.grid, "voltwatt", "volts", "watts"
            )

    def read_varwatt_data(self):
        """Reads and stores the entered data out of the controls for Var-Watt mode.

        The data is stored in the options control parameters.
        """
        self._extract_and_store_data_lists(
            self.ids.var_watt_tab_content.ids.grid, "varwatt", "vars", "watts"
            )

    def read_voltvar_and_voltwatt_data(self):
        """Reads and stores the entered data out of the controls for Volt-Var & Volt-Watt mode.

        The data is stored in the options control parameters.
        """
        self._extract_and_store_data_lists(
            self.ids.vv_vw_tab_content.ids.vv_grid, "vv_vw", "vv_volts", "vv_vars"
            )

        self._extract_and_store_data_lists(
            self.ids.vv_vw_tab_content.ids.vw_grid, "vv_vw", "vw_volts", "vw_watts"
            )

    def cancel(self):
        """Returns to the "configure-storage" form.

        This does not do anything with data.  It does not save any input data nor does it roll back
        any previously saved data.

        This is called when the user presses the "back" button.
        """
        self.read_all_data()
        self.manager.current = "configure-storage"
        self.manager.remove_widget(self)

    def _extract_and_store_data_lists(self, xyc: XYGridView, mode: str, l1name: str, l2name: str):
        """Reads the x and y data from the supplied grid and stores them in the control
        parameters using the supplied list keys.

        Parameters
        ----------
        l1name : str
            The key by which to store the "x" values read out of the grid into the
            control parameters
        l2name : str
            The key by which to store the "y" values read out of the grid into the
            control parameters
        """
        xl, yl = xyc.extract_data_lists()
        param_map = self._options.control.params[mode]
        param_map[l1name] = xl
        param_map[l2name] = yl


class PVConfigurationScreen(SSimBaseScreen):
    """Configure a single PV system."""

    def __init__(self, *args, **kwargs):
        self.pvsystem = None
        super().__init__(*args, **kwargs)

    def save(self):
        # TODO add the new storage device to the project
        self.manager.current = "der-config"

    def cancel(self):
        self.manager.current = "der-config"


class DERConfigurationScreen(SSimBaseScreen):
    """Configure energy storage devices and PV generators."""

    def __init__(self, *args, **kwargs):
        # comes first so the manager is initialized
        super().__init__(*args, **kwargs)
        self.ids.delete_storage.bind(
            on_release=self.delete_ess
        )

    def load_project_data(self):
        self.ids.ess_list.clear_widgets()
        for so in self.project.storage_devices:
            self.ids.ess_list.add_widget(
                StorageListItem(so, self)
            )

        for pv in self.project.pvsystems:
            self.ids.pv_list.add_widget(
                PVListItem(pv)
            )

    def new_storage(self):
        ess = StorageOptions("NewBESS", 3, [], [], [])

        self.add_ess(ess)

        self.manager.add_widget(
            StorageConfigurationScreen(
                self, ess, name="configure-storage")
        )

        self.manager.current = "configure-storage"

    def add_ess(self, ess):
        self.project.add_storage_option(ess)
        self.ids.ess_list.add_widget(
            StorageListItem(ess, self)
        )

    def delete_ess(self, button):
        to_remove = []
        for ess_list_item in self.ids.ess_list.children:
            if ess_list_item.selected:
                to_remove.append(ess_list_item)
                self.project.remove_storage_option(ess_list_item.ess)
        for widget in to_remove:
            self.ids.ess_list.remove_widget(widget)

    def on_pre_enter(self, *args):
        if self.project.grid_model is None:
            _show_no_grid_popup("ssim", self.manager)
        return super().on_pre_enter(*args)

    def edit_storage(self, ess_list_item):
        ess = ess_list_item.ess
        # Remove from the list so it can be re-added after editing
        #self.project.remove_storage_option(ess)
        #self.ids.ess_list.remove_widget(ess_list_item)
        self.manager.add_widget(
            StorageConfigurationScreen(self, ess, name="configure-storage"))
        self.manager.current = "configure-storage"


class StorageListItem(TwoLineAvatarIconListItem):
    def __init__(self, ess, der_screen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ess = ess
        self.text = ess.name
        self.secondary_text = str(ess.power)
        self.ids.edit.bind(
            on_release=self.edit
        )
        self._der_screen = der_screen

    @property
    def selected(self):
        return self.ids.selected.active

    def edit(self, icon_widget):
        self._der_screen.edit_storage(self)


class PVListItem(TwoLineAvatarIconListItem):
    def __init__(self, pv, der_screen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pv = pv
        self.text = pv.name
        self.secondary_text = str(pv.bus)
        self._der_screen = der_screen


class ResultsVariableListItemWithCheckbox(TwoLineAvatarIconListItem):
    def __init__(self, variable_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.config = config
        self.text = variable_name

    def toggle_selection(self):
        self.parent.parent.parent.parent.parent.parent.update_selected_variables()

    @property
    def selected(self):
        return self.ids.selected.active


class VariableListItem(TwoLineAvatarIconListItem):
    def __init__(self, pk=None, **kwargs):
        super().__init__(**kwargs)
        self.pk = pk

    @property
    def selected(self):
        return self.ids.selected.active

class LoadConfigurationScreen(SSimBaseScreen):
    pass


class MetricsNoGridPopupContent(BoxLayout):
    pass


class NoGridPopupContent(BoxLayout):
    pass


class MissingMetricValuesPopupContent(BoxLayout):
    pass


class MessagePopupContent(BoxLayout):
    pass


class BusListItemWithCheckbox(OneLineAvatarIconListItem):
    '''Custom list item.'''
    icon = StringProperty("android")

    def __int__(self, bus):
        self.text = bus
        self.bus = bus


class MetricListItem(TwoLineAvatarIconListItem):
    pass


class RightCheckbox(IRightBodyTouch, MDCheckbox):
    pass


class LeftCheckbox(ILeftBodyTouch, MDCheckbox):
    def toggle_configuration_check(self, check):
        print(check)
        if check.active:
            print('Configuration checked')
        print("selection made")


class MetricConfigurationScreen(SSimBaseScreen):

    _selBusses = []
    _currentMetricCategory = "None"
    _metricIcons = {"Bus Voltage": "lightning-bolt-circle", "Unassigned": "chart-line"}

    _def_btn_color = '#005376'

    def __reset_checked_bus_list(self):
        self._selBusses.clear()
        for wid in self.ids.interlist.children:
            if isinstance(wid, BusListItemWithCheckbox):
                cb = wid.ids.check
                if cb.active:
                    self._selBusses.append(cb)

    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self._refocus_field(self.ids.upperLimitText), 0.05)
        Clock.schedule_once(lambda dt: self._refocus_field(self.ids.lowerLimitText), 0.05)
        Clock.schedule_once(lambda dt: self._refocus_field(self.ids.objectiveText), 0.05)

    def _refocus_field(self, textfield):
        textfield.focus = True

    def set_sense(self, value):
        self.ids.caller.text = value
        self.menu.dismiss()

    def manage_store_button_enabled_state(self):
        self.ids.btnStore.disabled = len(self._selBusses) == 0

    def reload_metric_values(self):
        metrics = []
        common_lower_limit = None
        common_upper_limit = None
        common_obj = None
        common_sense = None
        have_no_metric_busses = False

        self.ids.metricValueBox.disabled = len(self._selBusses) == 0
        self.ids.metricSenseBox.disabled = len(self._selBusses) == 0

        ''' Gather up the list of all metrics relevant to the selection'''
        for b in self._selBusses:
            m = self.project.get_metric(self._currentMetricCategory, b)
            if m is None:
                have_no_metric_busses = True
            else:
                metrics.append(m)

        if not have_no_metric_busses:
            for m in metrics:
                if common_lower_limit is None:
                    common_lower_limit = m.metric.lower_limit
                    common_upper_limit = m.metric.upper_limit
                    common_obj = m.metric.objective
                    common_sense = m.metric.improvement_type
                else:
                    if common_lower_limit != m.metric.lower_limit:
                        common_lower_limit = None
                        break
                    if common_upper_limit != m.metric.upper_limit:
                        common_upper_limit = None
                        break
                    if common_obj != m.metric.objective:
                        common_obj = None
                        break
                    if common_sense != m.metric.improvement_type:
                        common_sense = None
                        break
        else:
            common_lower_limit = None
            common_upper_limit = None
            common_obj = None
            common_sense = None

        is_varied = len(metrics) > 1

        if common_lower_limit is None:
            self.ids.lowerLimitText.set_varied_mode() if is_varied else\
                self.ids.lowerLimitText.set_not_set_mode()
        else:
            self.ids.lowerLimitText.text = str(common_lower_limit)
            Clock.schedule_once(lambda dt: self._refocus_field(self.ids.lowerLimitText), 0.05)

        if common_upper_limit is None:
            self.ids.upperLimitText.set_varied_mode() if is_varied else\
                self.ids.upperLimitText.set_not_set_mode()
        else:
            self.ids.upperLimitText.text = str(common_upper_limit)
            Clock.schedule_once(lambda dt: self._refocus_field(self.ids.upperLimitText), 0.05)

        if common_obj is None:
            self.ids.objectiveText.set_varied_mode() if is_varied else\
                self.ids.objectiveText.set_not_set_mode()
        else:
            self.ids.objectiveText.text = str(common_obj)
            Clock.schedule_once(lambda dt: self._refocus_field(self.ids.objectiveText), 0.05)

        if common_sense is None:
            self.manage_button_selection_states(None)
        else:
            self.__active_sense_button(common_sense)

    def __active_sense_button(self, sense: ImprovementType):
        if sense == ImprovementType.Minimize:
            self.set_minimize_sense()
        elif sense == ImprovementType.Maximize:
            self.set_maximize_sense()
        else:
            self.set_seek_value_sense()

    def set_minimize_sense(self):
        """Sets the input state to indicate the Minimize sense.

        This manages the button selection states for the Minimize button.
        """
        self.manage_button_selection_states(self.ids.min_btn)

    def set_maximize_sense(self):
        """Sets the input state to indicate the Maximize sense.

        This manages the button selection states for the Maximize button.
        """
        self.manage_button_selection_states(self.ids.max_btn)

    def set_seek_value_sense(self):
        """Sets the input state to indicate the Seek Value sense.

        This manages the button selection states for the seek value button.
        """
        self.manage_button_selection_states(self.ids.seek_btn)

    def manage_button_selection_states(self, selButton):
        """Sets the state and color of all sense buttons in accordance with
        the supplied, desired selected button.

        Parameters
        ----------
        selButton:
            The button that is to be seleted and whose back color is to be that
            of the selected button.
        """
        self.ids.max_btn.selected = False
        self.ids.min_btn.selected = False
        self.ids.seek_btn.selected = False
        self.ids.max_btn.md_bg_color = self._def_btn_color
        self.ids.min_btn.md_bg_color = self._def_btn_color
        self.ids.seek_btn.md_bg_color = self._def_btn_color

        if selButton is self.ids.max_btn:
            self.ids.max_btn.md_bg_color = "red"
            self.ids.max_btn.selected = True

        elif selButton is self.ids.min_btn:
            self.ids.min_btn.md_bg_color = "red"
            self.ids.min_btn.selected = True

        elif selButton is self.ids.seek_btn:
            self.ids.seek_btn.md_bg_color = "red"
            self.ids.seek_btn.selected = True

    def store_metrics(self):
        """Extracts information from the input fields, creates the indicated
        metrics and stores them in the project.

        Inputs include limits, objective, sense, and list of selected busses.
        """
        lower_limit = parse_float(self.ids.lowerLimitText.text)
        upper_limit = parse_float(self.ids.upperLimitText.text)
        obj = parse_float(self.ids.objectiveText.text)
        sense = None

        if self.ids.max_btn.selected:
            sense = ImprovementType.Maximize
        elif self.ids.min_btn.selected:
            sense = ImprovementType.Minimize
        elif self.ids.seek_btn.selected:
            sense = ImprovementType.SeekValue

        err = Metric.validate_metric_values(lower_limit, upper_limit, obj, sense, False)

        if err:
            self.__show_invalid_metric_value_popup(err)
            return

        for bus in self._selBusses:
            accum = MetricTimeAccumulator(Metric(lower_limit, upper_limit, obj, sense))
            self.project.add_metric(self._currentMetricCategory, bus, accum)

        self.reload_metric_list()

    def reset_metric_list_label(self):
        """Resets the label atop the list of all defined metrics to include, or
           not, the current metric category.
        """
        if self._currentMetricCategory is None:
            self.ids.currMetriclabel.text = "Defined Metrics"

        elif self._currentMetricCategory == "None":
            self.ids.currMetriclabel.text = "Defined Metrics"

        else:
            self.ids.currMetriclabel.text = \
                "Defined \"" + self._currentMetricCategory + "\" Metrics"

    def manage_selection_buttons_enabled_state(self):
        numCldrn = len(self.ids.interlist.children) == 0
        self.ids.btnSelectAll.disabled = numCldrn
        self.ids.btnDeselectAll.disabled = numCldrn

    def deselect_all_metric_objects(self):
        for wid in self.ids.interlist.children:
            if isinstance(wid, BusListItemWithCheckbox):
                wid.ids.check.active = False

    def select_all_metric_objects(self):
        self._selBusses.clear()
        for wid in self.ids.interlist.children:
            if isinstance(wid, BusListItemWithCheckbox):
                wid.ids.check.active = True
                self._selBusses.append(wid.text)

    def reload_metric_list(self):
        """Reloads the list of all defined metrics.

        This method creates a list item for all metrics previously defined for
        the current category.
        """
        self.ids.metriclist.clear_widgets()
        self.reset_metric_list_label()
        manager = self.project.get_manager(self._currentMetricCategory)

        if manager is None: return

        list = self.ids.metriclist
        list.active = False
        for key, m in manager.all_metrics.items():
            txt = self._currentMetricCategory + " Metric for " + key
            deets = ""

            if m.metric.improvement_type == ImprovementType.Minimize:
                deets = "Upper Limit=" + str(m.metric.upper_limit) + ", " + \
                    "Objective=" + str(m.metric.objective) + ", " + \
                    "Sense=Minimize"

            elif m.metric.improvement_type == ImprovementType.Maximize:
                deets = "Lower Limit=" + str(m.metric.lower_limit) + ", " + \
                    "Objective=" + str(m.metric.objective) + ", " + \
                    "Sense=Maximize"

            elif m.metric.improvement_type == ImprovementType.SeekValue:
                deets = "Lower Limit=" + str(m.metric.lower_limit) + ", " + \
                    "Upper Limit=" + str(m.metric.upper_limit) + ", " + \
                    "Objective=" + str(m.metric.objective) + ", " + \
                    "Sense=Seek Value"

            bItem = MetricListItem(text=txt, secondary_text=deets)
            bItem.bus = key
            bItem.ids.left_icon.icon = self._metricIcons[self._currentMetricCategory]
            bItem.ids.trash_can.bind(on_release=self.on_delete_metric)
            list.add_widget(bItem)

        list.active = True

    def on_delete_metric(self, data):
        bus = data.listItem.bus
        self.project.remove_metric(self._currentMetricCategory, bus)
        self.reload_metric_list()
        self.reload_metric_values()

    def on_item_check_changed(self, ckb, value):
        bus = ckb.listItem.text
        if value:
            self._selBusses.append(bus)
        else:
            self._selBusses.remove(bus)

        self.reload_metric_values()
        self.manage_store_button_enabled_state()

    def configure_voltage_metrics(self):
        self._currentMetricCategory = "Bus Voltage"
        self.ids.interlabel.text = "Busses"
        self.load_bussed_into_list()
        self.reload_metric_list()
        self.reload_metric_values()
        self.manage_selection_buttons_enabled_state()

    def configure_some_other_metrics(self):
        self._currentMetricCategory = "Unassigned"
        self._selBusses.clear()
        self.ids.interlist.clear_widgets()
        self.ids.interlabel.text = "Metric Objects"
        self.reload_metric_list()
        self.reload_metric_values()
        self.manage_selection_buttons_enabled_state()
        print("I'm passing on the other issue...")

    def _return_to_main_screen(self, dt):
        self.manager.current = "ssim"

    def __show_missing_metric_value_popup(self):
        content = MissingMetricValuesPopupContent()

        popup = Popup(
            title='Missing Metric Values', content=content, auto_dismiss=False,
            size_hint=(0.4, 0.4)
            )
        content.ids.dismissBtn.bind(on_press=popup.dismiss)
        popup.open()
        return

    def __show_invalid_metric_value_popup(self, msg):
        content = MessagePopupContent()

        popup = Popup(
            title='Invalid Metric Values', content=content, auto_dismiss=False,
            size_hint=(0.4, 0.4)
            )
        content.ids.msg_label.text = str(msg)
        content.ids.dismissBtn.bind(on_press=popup.dismiss)
        popup.open()
        return

    def __show_no_grid_model_popup(self):
        content = MetricsNoGridPopupContent()

        popup = Popup(
            title='No Grid Model', content=content, auto_dismiss=False,
            size_hint=(0.4, 0.4)
            )
        content.ids.dismissBtn.bind(on_press=popup.dismiss)
        content.ids.mainScreenBtn.bind(on_press=popup.dismiss)
        content.ids.mainScreenBtn.bind(on_press=self._return_to_main_screen)
        popup.open()
        return

    def load_bussed_into_list(self):
        self._selBusses.clear()
        list = self.ids.interlist
        list.clear_widgets()
        list.text = "Busses"

        if self.project._grid_model is None:
            self.__show_no_grid_model_popup()
            return

        busses = self.project._grid_model.bus_names
        list.active = False
        for x in busses:
            bItem = BusListItemWithCheckbox(text=str(x))
            bItem.ids.check.bind(active=self.on_item_check_changed)
            list.add_widget(bItem)

        list.active = True


class RunSimulationScreen(SSimBaseScreen):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurations: List[Configuration] = []
        self.selected_configurations: List[Configuration] = []
        self.storage_options: List[StorageOptions] = []
        self._run_thread = None

    def on_enter(self):
        # # clear the MDList every time the RunSimulationScreen is opened
        # # TO DO: Keep track of selected configs
        self.ids.config_list.clear_widgets()
        self.configurations: List[Configuration] = []
        self.populate_configurations()

    def populate_configurations(self):
        # store all the project configurations into a list
        for config in self.project.configurations():
            self.configurations.append(config)
            print(config.id)

        # populate the UI with the list of configurations
        ctr = 1
        for config in self.configurations:
            secondary_detail_text = []
            tertiary_detail_text = []
            final_secondary_text = []
            final_tertiary_text = []

            for storage in config.storage:
                if storage is not None:
                    # print(storage)
                    secondary_detail_text.append(f"name: {storage.name}, bus: {storage.bus}")
                    tertiary_detail_text.append(f"kw: {storage.kw_rated}, kwh: {storage.kwh_rated}")
                else:
                    secondary_detail_text.append('no storage')
            final_secondary_text = "\n".join(secondary_detail_text)
            final_tertiary_text = "\n".join(tertiary_detail_text)

            self.ids.config_list.add_widget(
                    ListItemWithCheckbox(pk="pk",
                                         text=f"Configuration {ctr}",
                                         secondary_text=final_secondary_text,
                                         tertiary_text=final_tertiary_text)
            )
            ctr += 1

    def _evaluate(self):
        # step 1: check the configurations that are currently selected
        mdlist = self.ids.config_list # get reference to the configuration list
        self.selected_configurations = []
        print('selected configurations are:')
        no_of_configurations = len(self.configurations)
        ctr = no_of_configurations - 1
        for wid in mdlist.children:
            if wid.ids.check.active:
                print('*' * 20)
                print(wid.text)
                print('*' * 20)
                # extract a subset of selected configurations
                self.selected_configurations.append(self.configurations[ctr])
            ctr = ctr - 1
        # run all the configurations
        for config in self.selected_configurations:
            print(config)
            config.evaluate(basepath=self.project.base_dir)
            config.wait()

    def run_configurations(self):
        self._run_thread = Thread(target=self._evaluate)
        self._run_thread.start()

    def open_results_summary(self):
        self.manager.current = "results-summary"

    def open_visualize_results(self):
        self.manager.current = "results-visualize"

class ResultsVisualizeScreen(SSimBaseScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_results = ProjectResults(self.project)


class ResultsSummaryScreen(SSimBaseScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_results = ProjectResults(self.project)

    def on_enter(self):
        self.draw_canvas()
        for result in self.project_results.results():
            print(result.config_dir)

    def draw_canvas(self):
        # sample plot for testing purposes
        # TO DO: develop the backend for creating these plots
        # x_data = [1, 2, 3, 4, 5]
        # y_data = [1, 4, 9, 15, 25]
        # fig, ax = plt.subplots()
        # ax.plot(x_data, y_data)
        # ax.set_xlabel('Configuration #')
        # ax.set_ylabel('Aggregate Metics')

        accumulated_metric_fig = self.project_results.plot_accumulated_metrics()

        # Add Kivy widget to the canvas
        self.ids.summary_canvas.clear_widgets()
        self.ids.summary_canvas.add_widget(FigureCanvasKivyAgg(accumulated_metric_fig))

    def open_results_compare(self):
        self.manager.current = "results-compare"

    def open_results_detail(self):
        self.manager.current = "results-detail"


class ResultsCompareScreen(SSimBaseScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ResultsDetailScreen(SSimBaseScreen):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurations: List[Configuration] = []
        self.selected_variables= {}
        self.variables = {}
        self.current_configuration = None
        self.list_items = []
        self.selected_list_items = {}
        self.variable_data = pd.DataFrame()
        self.figure = None

    def on_enter(self):
        # populated `selected_list_items` assuming no selection from dropdown
        # menu
        # TO DO: Replace with evaluated configurations
        num_configs = len(list(self.project.configurations()))
        for ctr in range(num_configs):
            self.selected_list_items['Configuration ' + str(ctr+1)] = []

    def dismiss_popup(self):
        self._popup.dismiss()

    def _create_figure(self):
        fig = plt.figure()
        plt.clf()
        project_results = self.project_results.results()
        ctr = 1
        for result in project_results:
            _, data = result.storage_state()
            config_key = 'Configuration ' + str(ctr)
            # columns to plot
            columns_to_plot = self.selected_list_items[config_key]
            # select subset of data based on columns_to_plot
            selected_data = data[columns_to_plot]
            x_data = data.loc[:, 'time']
            # add the selected columns to plot
            for column in selected_data.keys():
                plt.plot(x_data, selected_data[column], label=config_key+'-'+column)
            ctr += 1

        plt.xlabel('time')
        if self.ids.detail_figure_ylabel.text is not None:
            plt.ylabel(self.ids.detail_figure_ylabel.text)
        plt.legend()
        if self.ids.detail_figure_title is not None:
            plt.title(self.ids.detail_figure_title.text)
        else:
            plt.title('Detail Plots')

        return fig

    def update_figure(self):
        self.figure = self._create_figure()
        Logger.debug("Figure update command issued from GUI ...")
        Logger.debug(self.ids.detail_figure_title.text)
        self.ids.detail_plot_canvas.clear_widgets()
        self.ids.detail_plot_canvas.add_widget(
            FigureCanvasKivyAgg(self.figure)
        )

    def save_figure_options(self):
        '''Saves the current active figure.'''
        chooser = SaveFigureDialog(
            save=self.save_figure, cancel=self.dismiss_popup
        )

        self._popup = Popup(title="save figure options", content=chooser)
        self._popup.open()

    def save_figure(self, path, filename):
        Logger.debug("Saving figure ... ")
        Logger.debug(filename)
        self.figure.savefig(filename+ '.png', dpi=300)

    def clear_figure(self):
        self.ids.detail_plot_canvas.clear_widgets()

    def drop_config_menu(self):
        for config in self.project.configurations():
            self.configurations.append(config)

        # TO DO: Replace with evaluated configurations
        num_configs = len(list(self.project.configurations()))
        # num_configs = self.project.num_configurations()

        menu_items = []
        for ctr in range(num_configs):
            display_text = "Configuration " + str(ctr+1)
            menu_items.append({
                "viewclass": "OneLineListItem",
                "text" : display_text,
                "on_release": lambda x=display_text: self.set_config(x)
            })

        self.menu = MDDropdownMenu(
            caller=self.ids.config_list_detail, items=menu_items, width_mult=5
        )
        self.menu.open()

    def update_selected_variables(self):
        print('Update selected variables called!')

        # self.selected_list_items = {}
        selected_items = []
        for variable in self.ids.variable_list_detail.children:
            if variable.selected:
                selected_items.append(variable.text)

        self.selected_list_items[self.current_configuration] = selected_items

        print(self.current_configuration)
        print(self.selected_list_items)


    def set_config(self, value):

        print(">>>>>>>>>>>>>>>>>>>>>>>>>")
        print(value)

        self.current_configuration = value

        print(self.selected_variables)
        # read the current selected configuration
        self.ids.config_list_detail.text = value

        # extract all results from all the configutations
        project_results = self.project_results.results()
        # obtain the index for the current selected configuration
        # TODO: setup a proper mapping system between Results and Configuration
        current_result_index = int(value[-1]) - 1
        # extract the `current_result` based on selection from drop down menu
        current_result = next(itertools.islice(project_results, current_result_index, None))

        # extract the data
        self.list_items, self.variable_data = current_result.storage_state()

        self.x_data = list(self.variable_data.loc[:, 'time'])

        self.ids.variable_list_detail.clear_widgets()
        # add the list of variables in the selected configuration
        # into the MDList

        Logger.debug('>>> Current selection records: ')
        Logger.debug(self.selected_list_items)

        for item in self.list_items:
            # do not add 'time' to the variable list
            if item == 'time':
                continue
            else:
                self.ids.variable_list_detail.add_widget(
                    ResultsVariableListItemWithCheckbox(variable_name = item)
                )

        # close the drop-down menu
        self.menu.dismiss()

class ListItemWithCheckbox(TwoLineAvatarIconListItem):

    def __init__(self, pk=None, **kwargs):
        super().__init__(**kwargs)
        self.pk = pk

    def delete_item(self, the_list_item):
        print("Delete icon was button was pressed")
        print(the_list_item)
        self.parent.remove_widget(the_list_item)


class LeftCheckbox(ILeftBodyTouch, MDCheckbox):
    '''Custom left container'''

    def __init__(self, pk=None, **kwargs):
        super().__init__(**kwargs)
        self.pk = pk

    def toggle_configuration_check(self, check):
        # print(check)
        # if check.active:
        #     print('Configuration checked')
        # print("selection made")
        pass


class SelectGridDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class LoadSSIMTOMLDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class SaveSSIMTOMLDialog(FloatLayout):
    save = ObjectProperty(None)
    cancel = ObjectProperty(None)

    def manage_filename_field(self):
        sel = self.ids.filechooser.selection[0]
        if os.path.isdir(sel):
            self.ids.filenamefield.text = ""
        else:
            self.ids.filenamefield.text = os.path.basename(sel)


class SaveFigureDialog(FloatLayout):
    save = ObjectProperty(None)
    cancel = ObjectProperty(None)
    text_input = ObjectProperty(None)

class SSimScreen(SSimBaseScreen):

    grid_path = ObjectProperty(None)

    def on_kv_post(self, base_widget):
        self.refresh_grid_plot()

    def report(self, message):
        Logger.debug("button pressed: %s", message)

    def dismiss_popup(self):
        self._popup.dismiss()

    def load_grid(self, path, filename):
        Logger.debug("loading file %s", filename[0])
        self.project.set_grid_model(filename[0])
        self.reset_grid_model_label()
        self.refresh_grid_plot()
        self.dismiss_popup()

    def reset_grid_model_label(self):
        self.ids.grid_model_label.text = "Grid Model: " + self.project._grid_model_path

    def reset_project_name_field(self):
        self.ids.project_name.text = self.project.name

    def load_toml_file(self, path, filename):
        Logger.debug("loading file %s", filename[0])
        self.project.load_toml_file(filename[0])
        self.set_current_input_file(filename[0])
        self.reset_grid_model_label()
        self.reset_project_name_field()
        self.refresh_grid_plot()
        self.dismiss_popup()

    def set_current_input_file(self, fullpath):
        self.project._input_file_path = fullpath
        app = MDApp.get_running_app()
        app.title = "SSim: " + fullpath

    def save_toml_file(self, selection, filename):
        fullpath = selection[0]

        split = os.path.splitext(filename)
        if split[1].lower() != ".toml":
            filename = filename + ".toml"

        if os.path.isdir(fullpath):
            fullpath = os.path.join(fullpath, filename)
        else:
            fullpath = os.path.join(os.path.dirname(fullpath), filename)

        Logger.debug("saving file %s", fullpath)

        self.set_current_input_file(fullpath)
        toml = self.project.write_toml()

        with open(fullpath, 'w') as f:
            f.write(toml)

        self.dismiss_popup()

    def read_toml(self):
        chooser = LoadSSIMTOMLDialog(
            load=self.load_toml_file, cancel=self.dismiss_popup)

        self._popup = Popup(title="select SSIM TOML file", content=chooser)
        self._popup.open()

    def write_to_toml(self):
        if not self.project._input_file_path:
            self.write_as_toml()
            return

        fname = os.path.basename(self.project._input_file_path)
        dname = [os.path.dirname(self.project._input_file_path)]

        self.save_toml_file(dname, fname)

    def write_as_toml(self):
        chooser = SaveSSIMTOMLDialog(
            save=self.save_toml_file, cancel=self.dismiss_popup)

        self._popup = Popup(title="select SSIM TOML file", content=chooser)
        self._popup.open()

    def select_grid_model(self):
        chooser = SelectGridDialog(
            load=self.load_grid, cancel=self.dismiss_popup)

        self._popup = Popup(title="select grid model", content=chooser)
        self._popup.open()

    def open_der_configuration(self):
        self.manager.current = "der-config"

    def open_load_configuration(self):
        self.manager.current = "load-config"

    def open_metric_configuration(self):
        self.manager.current = "metric-config"

    def do_run_simulation(self):
        self.manager.current = "run-sim"
        if self.project.grid_model is None:
            _show_no_grid_popup("ssim", self.manager)
            return

    def num_phases(self, line):
        dssdirect.Lines.Name(line)
        return dssdirect.Lines.Phases()

    def get_raw_bus_name(self, bus: str):
        return bus.split(".", 1)[0]

    def bus_coords(self, bus):
        dssdirect.Circuit.SetActiveBus(bus)
        return dssdirect.Bus.X(), dssdirect.Bus.Y()

    def line_bus_coords(self, line):
        bus1, bus2 = self.line_busses(line)
        return [self.bus_coords(bus1), self.bus_coords(bus2)]

    def line_busses(self, line):
        dssdirect.Lines.Name(line)
        return [dssdirect.Lines.Bus1(), dssdirect.Lines.Bus2()]

    #def plot_line(self, line):
    #    x, y = zip(*line_bus_coords(line))
    #    if (0 in x) and (0 in y):
    #        return
    #    plt.plot(x, y, color='gray', solid_capstyle='round')

    def _distance_meters(self, latitude1, longitude1, latitude2, longitude2):
        """Return distance between two points in meters"""
        # Use the mean latitude to get a reasonable approximation
        latitude = (latitude1 + latitude2) / 2
        m_per_degree_lat = 111132.92 - 559.82 * cos(2 * latitude) \
                           + 1.175 * cos(4 * latitude) \
                           - 0.0023 * cos(6 * latitude)
        m_per_degree_lon = 111412.84 * cos(latitude) \
                           - 93.5 * cos(3 * latitude) \
                           + 0.118 * cos(5 * latitude)
        y = (latitude1 - latitude2) * m_per_degree_lat
        x = (longitude1 - longitude2) * m_per_degree_lon
        return hypot(x, y)

    def _get_substation_location(self):
        """Return gps coordinates of the substation.

        Returns
        -------
        latitude : float
        longitude : float
        """
        if not dssdirect.Solution.Converged():
            dssdirect.Solution.Solve()
        busses = dssdirect.Circuit.AllBusNames()
        distances = dssdirect.Circuit.AllBusDistances()
        substation = sorted(zip(busses, distances), key=lambda x: x[1])[0][0]
        dssdirect.Circuit.SetActiveBus(substation)
        return dssdirect.Bus.Y(), dssdirect.Bus.X()

    def group(self, x):
        if x < 0.33:
            return 1
        if x < 0.66:
            return 2
        return 3

    def changed_show_bus_labels(self, active_state):
        self.refresh_grid_plot()


    def refresh_grid_plot(self):
        gm = self.project.grid_model
        plt.clf()

        if gm is None:
            self.ids.grid_diagram.display_plot_error(
                "There is no current grid model."
            )
            return

        lines = gm.line_names
        busses = gm.bus_names

        if len(lines) == 0 and len(busses) == 0:
            self.ids.grid_diagram.display_plot_error(
                "There are no lines and no busses in the current grid model."
            )
            return

        # Start by plotting the lines if there are any.  Note that if there are lines,
        # there must be busses but the opposite may not be true.
        plotlines = len(lines) > 0

        seg_busses = {}

        if plotlines > 0:
            seg_lines = [line for line in lines
                         if (0., 0.) not in self.line_bus_coords(line)]

            for line in seg_lines:
                bus1, bus2 = self.line_busses(line)
                bc1 = self.bus_coords(bus1)
                bc2 = self.bus_coords(bus2)
                seg_busses[self.get_raw_bus_name(bus1)] = bc1
                seg_busses[self.get_raw_bus_name(bus2)] = bc2


            line_segments = [self.line_bus_coords(line)  for line in seg_lines]

            if len(line_segments) == 0:
                self.ids.grid_diagram.display_plot_error(
                    "There are lines but their bus locations are not known so no meaningful plot can be produced."
                )
                return

            #line_widths = [num_phases(line) for line in lines[:-1]]

            #substation_lat, substation_lon = self._get_substation_location()
            #distance = functools.partial(self._distance_meters, substation_lat, substation_lon)

            #distances = [min(distance(b1[1], b1[0]), distance(b2[1], b2[0]))  # / 2.0
            #             for b1, b2 in line_segments]

            #groups = [self.group(dist / max(distances)) for dist in distances]

            lc = LineCollection(
                line_segments, norm=plt.Normalize(1, 3), cmap='tab10'
                )  # , linewidths=line_widths)

            lc.set_capstyle('round')
            #lc.set_array(np.array(groups))

            fig, ax = plt.subplots()
            fig.tight_layout()

            ax.add_collection(lc)
            ax.axis("off")

            xs, ys = zip(*[(x, y) for seg in line_segments for x, y in seg])
            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)

        else:
            for bus in busses:
                bc = self.bus_coords(bus)
                seg_busses[self.get_raw_bus_name(bus)] = bc

            xs, ys = zip(*[(x, y) for seg in seg_busses for x, y in seg_busses[seg]])
            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)

        x = [seg_busses[bus][0] for bus in seg_busses]
        y = [seg_busses[bus][1] for bus in seg_busses]

        ax.scatter(x, y)

        if self.ids.show_bus_labels.active:
            for bus in seg_busses:
                loc = seg_busses[bus]
                ax.annotate(bus, (loc[0], loc[1]))

        #plt.title("Grid Layout")

        #xlocs, xlabels = plt.xticks()
        #ylocs, ylabels = plt.yticks()
        #plt.xticks(ticks=xlocs, labels=[])
        #plt.yticks(ticks=ylocs, labels=[])
        #plt.grid()
        plt.xticks([])
        plt.yticks([])

        ax.set_xlim(min(xs) - 0.05 * (max_x - min_x), max(xs) + 0.05 * (max_x - min_x))
        ax.set_ylim(min(ys) - 0.05 * (max_y - min_y), max(ys) + 0.05 * (max_y - min_y))

        dg = self.ids.grid_diagram
        dg.reset_plot()

# class ResultsVisualizationTab(FloatLayout, MDTabsBase):
#     pass


def _show_no_grid_popup(dismiss_screen=None, manager=None):
    """Show a popup dialog warning that no grid model is selected.

    Parameters
    ----------
    dismiss_screen : str, optional

    """
    poppup_content = NoGridPopupContent()
    poppup_content.orientation = "vertical"
    popup = Popup(title='No Grid Model', content=poppup_content,
                  auto_dismiss=False, size_hint=(0.4, 0.4))

    def dismiss(*args):
        popup.dismiss()
        if (dismiss_screen is not None) and (manager is not None):
            manager.current = dismiss_screen

    poppup_content.ids.dismissBtn.bind(on_press=dismiss)
    # open the popup
    popup.open()


def _make_xy_matlab_plot(mpb: MatlabPlotBox, xs: list, ys: list, xlabel: str, ylabel: str, title: str):
    """A utility method to plot the xs and ys in the given box.  The supplied title
    and axis labels are installed.

    Parameters
    ----------
    mpb: MatlabPlotBox
        The plot box that will house the plot created.
    xs: list
        The list of x values to plot.  Should be a list of floats.
    ys: list
        The list of y values to plot.  Should be a list of floats.
    xlabel: str
        The x axis label to put on the created plot.
    ylabel: str
        The y axis label to put on the created plot.
    title: str
        The string to use as the plot title.
    """
    fig, ax = plt.subplots(1, 1, layout="constrained")
    ax.plot(xs, ys, marker='o')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.title(title)
    mpb.reset_plot()


def _configure_fonts(exo_regular, exo_bold, exo_italic,
                     opensans_regular, opensans_bold, opensans_italic):

    # Configure the fonts use but the quest style
    LabelBase.register(
        name='Exo 2',
        fn_regular=exo_regular,
        fn_bold=exo_bold,
        fn_italic=exo_italic
    )

    LabelBase.register(
        name='Open Sans',
        fn_regular=opensans_regular,
        fn_bold=opensans_bold,
        fn_italic=opensans_italic
    )


def _paths(package, names):
    basepath = files(package)
    # all names need to be referenced individually so that each file
    # is guaranteed to exist when they are referenced.  As far as I
    # can tell there is no way to just make a directory containing all
    # resources in a package using importlib_resources.
    return list(as_file(basepath.joinpath(name)) for name in names)


def _font_paths():
    return dict(
        zip(_FONT_FILES.keys(),
            _paths("ssim.ui.kivy.fonts", _FONT_FILES.values()))
    )


def _kv_paths():
    return _paths("ssim.ui.kivy", _KV_FILES)


def _image_paths():
    return _paths("ssim.ui.kivy.images", _IMAGE_FILES)


def main():
    """Run the storage-sim kivy application."""
    Logger.setLevel(LOG_LEVELS["debug"])
    with ExitStack() as stack:
        font_paths = {font_name: str(stack.enter_context(font_path))
                      for font_name, font_path in _font_paths().items()}
        kv_paths = [stack.enter_context(kv) for kv in _kv_paths()]
        image_paths = [stack.enter_context(img) for img in _image_paths()]
        _configure_fonts(**font_paths)
        resource_dirs = set(
            resource.parent
            for resource in itertools.chain(kv_paths, image_paths)
        )
        for resource_dir in resource_dirs:
            kivy.resources.resource_add_path(resource_dir)
        SSimApp().run()


if __name__ == '__main__':
    main()
