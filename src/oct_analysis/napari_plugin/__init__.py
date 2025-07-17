from oct_analysis.napari_plugin import widgets
from qtpy.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QTabWidget
from magicgui.widgets import Container
from magicgui import magicgui
import json
from pathlib import Path

def main():

    # save-settings funktion. später ersetzen durch class-struktur des widgets.py inhalts
    @magicgui(call_button="Save Settings",
            settings_file={"widget_type": "FileEdit", "mode": "w", "value": str(Path.home() / "settings.json")}
    )
    def save_settings(settings_file):
        settings = {}
        for widget in labeling_widgets:
            params = {}
            # Die ursprünglichen Parameter stehen in __signature__.parameters
            for param in widget.__signature__.parameters:
                if param == "viewer":
                    continue  # viewer ist nicht serialisierbar
                w = widget.get_widget(param)
                if w is not None:
                    val = w.value
                    if isinstance(val, Path):
                        val = str(val)
                    params[param] = val
            settings[widget.name or widget.__class__.__name__] = params

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
    #

    # Instructions Tab
    instructions_widgets = [
        widgets.show_instructionsA,
        widgets.show_instructionsB,
        widgets.show_instructionsC,
        widgets.show_instructionsD
    ]
    scrolltab_instructions = create_scrolltab(
        widget_list=instructions_widgets,
        name='Instructions'
    )
    
    # Labeling Tab
    labeling_widgets = [
        widgets.load_oct,
        widgets.median_filter,
        widgets.roi_filter_2D,
        widgets.locate_window,
        widgets.zero_out_window,
        widgets.locate_substratum,
        widgets.zero_out_substratum,
        widgets.increase_contrast,
        widgets.binarize,
        widgets.remove_outliers,
        widgets.confirm_binarization,
        save_settings,
        widgets.save
    ]
    scrolltab_labeling = create_scrolltab(
        widget_list=labeling_widgets,
        name='Labeling'
    )

    # Post-Processing Tab
    post_widgets = [
        widgets.count_voxels
    ]
    scrolltab_post = create_scrolltab(
        widget_list=post_widgets,
        name='Post-Processing'
    )
    
    # Merge Tabs
    tabs = QTabWidget()
    tabs.addTab(scrolltab_instructions, "Instructions")
    tabs.addTab(scrolltab_labeling, "Labeling")
    tabs.addTab(scrolltab_post, "Post-Processing")

    return tabs


# helper functions
def create_scrolltab(widget_list, name="", min_width=300):
    container = Container(
        widgets=widget_list,
        layout='vertical',
        name=name,
        visible=True,
        labels=False
    )

    inner_widget = QWidget()
    inner_layout = QVBoxLayout(inner_widget)
    inner_layout.addWidget(container.native)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner_widget)
    scroll.setMinimumWidth(min_width)

    scrolltab = scroll

    return scrolltab
