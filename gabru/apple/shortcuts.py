import plistlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from gabru.log import Logger

"""
iOS Shortcut Builder
A clean, extendable library for generating iOS/iPadOS shortcut files programmatically.

source: claude-sonnet-4.5
"""

log = Logger.get_log('ShortcutBuilder')


class HTTPMethod(Enum):
    """Supported HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class ShortcutAction:
    """Base class for shortcut actions"""
    identifier: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary format"""
        return {
            "WFWorkflowActionIdentifier": self.identifier,
            "WFWorkflowActionParameters": self.parameters
        }


class ShortcutBuilder:
    """
    Builder class for creating iOS shortcuts programmatically.

    Usage:
        builder = ShortcutBuilder("My Shortcut")
        builder.add_get_request("https://example.com/api")
        builder.add_notification("Done!", "Request completed")
        builder.save("my_shortcut.shortcut")
    """

    def __init__(self, name: str):
        """
        Initialize a new shortcut builder.

        Args:
            name: Display name for the shortcut
        """
        self.name = name
        self.actions: List[ShortcutAction] = []
        self.icon_color = 4282601983  # Blue
        self.icon_glyph = 59511  # Default glyph

    def add_action(self, action: ShortcutAction) -> 'ShortcutBuilder':
        """
        Add a custom action to the shortcut.

        Args:
            action: ShortcutAction instance

        Returns:
            self for method chaining
        """
        self.actions.append(action)
        return self

    # HTTP Request Actions

    def add_get_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> 'ShortcutBuilder':
        """
        Add a GET request action.

        Args:
            url: The URL to request
            headers: Optional HTTP headers dictionary
        """
        params = {
            "WFURL": url,
            "WFHTTPMethod": HTTPMethod.GET.value
        }

        if headers:
            params["WFHTTPHeaders"] = headers
            params["ShowHeaders"] = True

        action = ShortcutAction("is.workflow.actions.downloadurl", params)
        return self.add_action(action)

    def add_post_request(
            self,
            url: str,
            body: Optional[str] = None,
            json_body: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None
    ) -> 'ShortcutBuilder':
        """
        Add a POST request action.

        Args:
            url: The URL to request
            body: Raw request body (string)
            json_body: JSON body (dict) - will be converted to JSON
            headers: Optional HTTP headers dictionary
        """
        params = {
            "WFURL": url,
            "WFHTTPMethod": HTTPMethod.POST.value
        }

        # Handle JSON body by creating it as text first
        if json_body:
            # Add a text action with the JSON content first
            json_string = json.dumps(json_body)
            self.add_text(json_string)

            # Then use "Provided by previous output" for the body
            params["WFHTTPBodyType"] = "JSON"
            # This tells Shortcuts to use the output from the previous action

            # Set Content-Type header
            if headers and "Content-Type" not in headers:
                headers = headers.copy()
                headers["Content-Type"] = "application/json"
            elif not headers:
                headers = {"Content-Type": "application/json"}

        elif body:
            params["WFHTTPBodyType"] = "Text"
            params["WFRequestVariable"] = {
                "Value": {
                    "string": body
                },
                "WFSerializationType": "WFTextTokenString"
            }

        if headers:
            params["WFHTTPHeaders"] = headers
            params["ShowHeaders"] = True

        action = ShortcutAction("is.workflow.actions.downloadurl", params)
        return self.add_action(action)

    # UI Actions

    def add_notification(self, title: str, body: str = "") -> 'ShortcutBuilder':
        """
        Add a notification action.

        Args:
            title: Notification title
            body: Notification body text
        """
        params = {
            "WFNotificationActionTitle": title,
            "WFNotificationActionBody": body
        }
        action = ShortcutAction("is.workflow.actions.notification", params)
        return self.add_action(action)

    def add_show_alert(self, title: str, message: str = "", show_cancel: bool = True) -> 'ShortcutBuilder':
        """
        Add a show alert action.

        Args:
            title: Alert title
            message: Alert message
            show_cancel: Whether to show cancel button
        """
        params = {
            "WFAlertActionTitle": title,
            "WFAlertActionMessage": message,
            "WFAlertActionCancelButtonShown": show_cancel
        }
        action = ShortcutAction("is.workflow.actions.alert", params)
        return self.add_action(action)

    def add_show_result(self, text: Optional[str] = None) -> 'ShortcutBuilder':
        """
        Add a show result action (displays text/previous output).

        Args:
            text: Optional text to display. If None, shows previous action's output
        """
        params = {}
        if text:
            params["Text"] = text

        action = ShortcutAction("is.workflow.actions.showresult", params)
        return self.add_action(action)

    # Input Actions

    def add_ask_for_input(
            self,
            prompt: str,
            default_value: str = "",
            input_type: str = "Text"
    ) -> 'ShortcutBuilder':
        """
        Add an ask for input action.

        Args:
            prompt: The prompt to show user
            default_value: Default value in input field
            input_type: Type of input ("Text", "Number", "URL", "Date")
        """
        params = {
            "WFAskActionPrompt": prompt,
            "WFAskActionDefaultAnswer": default_value,
            "WFInputType": input_type
        }
        action = ShortcutAction("is.workflow.actions.ask", params)
        return self.add_action(action)

    # Text Actions

    def add_text(self, text: str) -> 'ShortcutBuilder':
        """
        Add a text action (creates text output).

        Args:
            text: The text content
        """
        params = {"WFTextActionText": text}
        action = ShortcutAction("is.workflow.actions.gettext", params)
        return self.add_action(action)

    def add_comment(self, text: str) -> 'ShortcutBuilder':
        """
        Add a comment action (for documentation).

        Args:
            text: Comment text
        """
        params = {"WFCommentActionText": text}
        action = ShortcutAction("is.workflow.actions.comment", params)
        return self.add_action(action)

    # URL Actions

    def add_url(self, url: str) -> 'ShortcutBuilder':
        """
        Add a URL action (creates URL output).

        Args:
            url: The URL
        """
        params = {"WFURLActionURL": url}
        action = ShortcutAction("is.workflow.actions.url", params)
        return self.add_action(action)

    def add_open_url(self, url: Optional[str] = None) -> 'ShortcutBuilder':
        """
        Add an open URL action.

        Args:
            url: URL to open. If None, opens the previous action's output
        """
        params = {}
        if url:
            params["WFInput"] = url

        action = ShortcutAction("is.workflow.actions.openurl", params)
        return self.add_action(action)

    # Variable Actions

    def add_set_variable(self, variable_name: str) -> 'ShortcutBuilder':
        """
        Add a set variable action (stores previous output).

        Args:
            variable_name: Name of the variable
        """
        params = {"WFVariableName": variable_name}
        action = ShortcutAction("is.workflow.actions.setvariable", params)
        return self.add_action(action)

    def add_get_variable(self, variable_name: str) -> 'ShortcutBuilder':
        """
        Add a get variable action (retrieves stored variable).

        Args:
            variable_name: Name of the variable to retrieve
        """
        params = {
            "WFVariable": {
                "Value": {
                    "Type": "Variable",
                    "VariableName": variable_name
                },
                "WFSerializationType": "WFTextTokenAttachment"
            }
        }
        action = ShortcutAction("is.workflow.actions.getvariable", params)
        return self.add_action(action)

    # Utility Actions

    def add_wait(self, seconds: float) -> 'ShortcutBuilder':
        """
        Add a wait/delay action.

        Args:
            seconds: Number of seconds to wait
        """
        params = {"WFDelayTime": seconds}
        action = ShortcutAction("is.workflow.actions.delay", params)
        return self.add_action(action)

    def add_get_current_date(self) -> 'ShortcutBuilder':
        """Add a get current date action."""
        action = ShortcutAction("is.workflow.actions.date", {})
        return self.add_action(action)

    # Styling

    def set_icon(self, color: int = 4282601983, glyph: int = 59511) -> 'ShortcutBuilder':
        """
        Set the shortcut icon.

        Args:
            color: Icon color (integer color code)
            glyph: Icon glyph number
        """
        self.icon_color = color
        self.icon_glyph = glyph
        return self

    # Build and Save

    def build(self) -> Dict[str, Any]:
        """
        Build the shortcut dictionary.

        Returns:
            Dictionary representing the shortcut
        """
        return {
            "WFWorkflowActions": [action.to_dict() for action in self.actions],
            "WFWorkflowClientRelease": "2.2.2",
            "WFWorkflowClientVersion": "900",
            "WFWorkflowIcon": {
                "WFWorkflowIconStartColor": self.icon_color,
                "WFWorkflowIconGlyphNumber": self.icon_glyph
            },
            "WFWorkflowImportQuestions": [],
            "WFWorkflowInputContentItemClasses": [
                "WFAppStoreAppContentItem",
                "WFArticleContentItem",
                "WFContactContentItem",
                "WFDateContentItem",
                "WFEmailAddressContentItem",
                "WFGenericFileContentItem",
                "WFImageContentItem",
                "WFiTunesProductContentItem",
                "WFLocationContentItem",
                "WFDCMapsLinkContentItem",
                "WFAVAssetContentItem",
                "WFPDFContentItem",
                "WFPhoneNumberContentItem",
                "WFRichTextContentItem",
                "WFSafariWebPageContentItem",
                "WFStringContentItem",
                "WFURLContentItem"
            ],
            "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientVersionString": "900",
            "WFWorkflowOutputContentItemClasses": [],
            "WFWorkflowTypes": []
        }

    def save(self, filepath: str) -> str:
        """
        Save the shortcut to a .shortcut file.

        Args:
            filepath: Output filename (will add .shortcut if not present)

        Returns:
            The filename that was saved
        """
        if not filepath.endswith('.shortcut'):
            filepath += '.shortcut'

        shortcut_dict = self.build()
        plist_data = plistlib.dumps(shortcut_dict, fmt=plistlib.FMT_BINARY)

        with open(filepath, 'wb') as f:
            f.write(plist_data)

        log.info(f"✓ Saved: {filepath}")
        return filepath
