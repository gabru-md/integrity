import re


class Lexer:
    """
    Tokenizes the Sentinel Contract Language (SCL).
    Order is crucial: more specific patterns (like CLOCK_VALUE) must come first.
    """

    def __init__(self):
        self.token_patterns = [
            ('NOT', r'NOT'),
            ('WITHIN', r'WITHIN'),
            ('SINCE', r'SINCE'),  # NEW Temporal Keyword
            ('TIME_UNIT', r's|m|h'),
            ('CLOCK_VALUE', r'\d{4}'),  # HIGH PRIORITY: Must match 4-digit time
            ('NUMBER', r'\d+'),  # Lower priority
            ('OPERATOR', r'x'),
            ('LOGICAL_OP', r'AND|OR'),
            ('TRIGGER_KEYWORD', r'AFTER'),  # The main contract delimiter
            ('CLOCK_KEYWORD', r'CLOCK'),
            ('BETWEEN_KW', r'BETWEEN'),
            ('TEMPORAL_KW', r'AFTER|BEFORE'),  # Temporal operators for CLOCK
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('COMMA', r','),
            ('EVENT_NAME', r'[a-zA-Z_:]+'),
            ('WHITESPACE', r'\s+'),
        ]
        self.token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.token_patterns)

    def tokenize(self, text):
        tokens = []
        for match in re.finditer(self.token_regex, text):
            kind = match.lastgroup
            if kind == 'WHITESPACE':
                continue

            # Simple list of token dictionaries
            tokens.append({'type': kind, 'value': match.group(0)})
        return tokens


class ASTNode:
    def __init__(self, type, value=None, children=None):
        self.type = type
        self.value = value
        self.children = children if children is not None else []

    def __repr__(self):
        return f"Node({self.type}, value={self.value}, children={self.children})\n"


def ast_to_contract_dict(ast_node):
    """Converts the AST to the required dictionary structure for the Evaluator."""
    if ast_node.type == 'CONTRACT':
        # The CONTRACT node now holds only the conditions, the trigger is handled outside this block
        trigger_node, conditions_node = ast_node.children
        return {
            "name": "Generated Contract",
            "trigger": trigger_node.value,
            "conditions": ast_to_contract_dict(conditions_node)
        }

    if ast_node.type in ('AND', 'OR'):
        return {
            "operator": ast_node.type,
            "terms": [ast_to_contract_dict(child) for child in ast_node.children]
        }

    if ast_node.type == 'NOT':
        return {
            "operator": "NOT",
            "terms": [ast_to_contract_dict(ast_node.children[0])]
        }

    if ast_node.type == 'TEMPORAL_CONDITION':
        # Handles 2x event WITHIN 1h logic
        condition_dict = ast_to_contract_dict(ast_node.children[0])
        condition_dict["time_window"] = ast_node.value["number"]
        condition_dict["unit"] = ast_node.value["unit"]
        return condition_dict

    if ast_node.type == 'CLOCK_CHECK':
        return {
            "type": "clock_check",
            "time_range": ast_node.value
        }

    if ast_node.type == 'HISTORY_CHECK':
        # NEW: Handles EVENT_A SINCE EVENT_B
        return {
            "type": "history_check",
            "event": ast_node.value["event"],
            "since_event": ast_node.value["since_event"]
        }

    if ast_node.type == 'COUNTED_EVENT':
        # Handles both 1x event and Nx event logic
        count = ast_node.value
        event_name = ast_node.children[0].value
        return {
            "type": "event_count",
            "event": event_name,
            "min_count": count
        }

    if ast_node.type == 'EVENT':
        # Simple event presence check (treated as 1x count)
        event_name = ast_node.value
        return {
            "type": "event_count",
            "event": event_name,
            "min_count": 1
        }

    raise ValueError(f"Unknown AST node type: {ast_node.type}")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def lookahead(self, offset=1):
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return None

    def consume(self, expected_type=None, expected_value=None):
        token = self.current_token()
        if not token:
            raise ValueError("Unexpected end of input.")
        if expected_type and token['type'] != expected_type:
            raise ValueError(f"Expected token of type '{expected_type}', got '{token['type']}' at position {self.pos}")
        if expected_value and token['value'] != expected_value:
            raise ValueError(f"Expected token value '{expected_value}', got '{token['value']}' at position {self.pos}")
        self.pos += 1
        return token

    def parse_event(self):
        event_token = self.consume('EVENT_NAME')
        return ASTNode('EVENT', value=event_token['value'])

    def parse_duration(self):
        self.consume('WITHIN')
        number_token = self.consume('NUMBER')
        unit_token = self.consume('TIME_UNIT')
        return {"number": int(number_token['value']), "unit": unit_token['value']}

    def parse_clock_term(self):
        """Parses: CLOCK(HHMM) [AFTER | BEFORE | BETWEEN CLOCK(HHMM)]"""
        self.consume('CLOCK_KEYWORD', 'CLOCK')
        self.consume('LPAREN')
        time1 = self.consume('CLOCK_VALUE')['value']
        self.consume('RPAREN')

        token = self.current_token()
        temporal_op = "AFTER"  # DEFAULT: If no keyword follows, assume AFTER
        time2 = None

        if token and token['type'] in ('TEMPORAL_KW'):
            # Explicit temporal keyword used (AFTER or BEFORE)
            temporal_op = self.consume('TEMPORAL_KW')['value']
        elif token and token['type'] == 'BETWEEN_KW':
            # Explicit BETWEEN range used
            self.consume('BETWEEN_KW', 'BETWEEN')
            self.consume('CLOCK_KEYWORD', 'CLOCK')
            self.consume('LPAREN')
            time2 = self.consume('CLOCK_VALUE')['value']
            self.consume('RPAREN')
            temporal_op = "BETWEEN"

        time_range = {
            "op": temporal_op,
            "time1": time1,
            "time2": time2
        }

        return ASTNode('CLOCK_CHECK', value=time_range)

    def parse_temporal_event_term(self):
        """
        Parses either:
        1. [N]x EVENT_NAME
        2. [N]x EVENT_NAME WITHIN [D] TIME_UNIT
        3. EVENT_NAME SINCE EVENT_NAME
        """
        is_counted = self.current_token() and self.current_token()['type'] == 'NUMBER'

        if is_counted:
            count = int(self.consume('NUMBER')['value'])
            self.consume('OPERATOR', 'x')
            event_node = self.parse_event()
            node = ASTNode('COUNTED_EVENT', value=count, children=[event_node])
        else:
            node = self.parse_event()

        # Check for SINCE
        if self.current_token() and self.current_token()['type'] == 'SINCE':
            if is_counted:
                raise ValueError("SINCE cannot follow a COUNT (e.g., '2x event SINCE...')")
            self.consume('SINCE')
            since_event_node = self.parse_event()
            return ASTNode('HISTORY_CHECK', value={
                "event": node.value,
                "since_event": since_event_node.value
            })

        # Check for WITHIN
        if self.current_token() and self.current_token()['type'] == 'WITHIN':
            duration = self.parse_duration()
            return ASTNode('TEMPORAL_CONDITION', value=duration, children=[node])

        return node  # Simple EVENT or COUNTED_EVENT

    def parse_term(self):
        """
        Parses a single term which can be:
        ( Condition ) | NOT Term | CLOCK(HHMM) | Temporal_Event_Term
        """
        token = self.current_token()
        if not token:
            raise ValueError("Unexpected end of input while parsing term.")

        if token['type'] == 'LPAREN':
            self.consume('LPAREN')
            sub_condition_node = self.parse_condition()
            self.consume('RPAREN')
            return sub_condition_node

        if token['type'] == 'NOT':
            self.consume('NOT')
            # NOT must be followed by a single term (event or clock)
            term_node = self.parse_term()
            return ASTNode('NOT', children=[term_node])

        if token['type'] == 'CLOCK_KEYWORD':
            return self.parse_clock_term()

        if token['type'] in ('NUMBER', 'EVENT_NAME'):
            return self.parse_temporal_event_term()

        raise ValueError(f"Unexpected token type '{token['type']}' starting a term at position {self.pos}")

    def parse_condition(self):
        """Parses terms separated by AND/OR (Logic Operators)"""
        left_node = self.parse_term()

        while self.current_token() and self.current_token()['type'] == 'LOGICAL_OP':
            op_token = self.consume()
            right_node = self.parse_term()
            # Grouping: Always make the logical operator the parent of the two terms
            left_node = ASTNode(op_token['value'], children=[left_node, right_node])
        return left_node

    def parse_contract(self):
        """Parses the full contract: EVENT_A AFTER CONDITION"""
        trigger_event_node = self.parse_event()
        # The main 'AFTER' is a TRIGGER_KEYWORD and separates the trigger from the conditions
        self.consume('TRIGGER_KEYWORD', 'AFTER')
        conditions_node = self.parse_condition()

        # Returns the full contract AST structure
        return ASTNode('CONTRACT', children=[trigger_event_node, conditions_node])

    def parse_contract_as_dict(self):
        ast_node = self.parse_contract()
        return ast_to_contract_dict(ast_node)


lexer = Lexer()


def parse_contract_as_dict(contract_str: str):
    parser = Parser(lexer.tokenize(contract_str))
    return parser.parse_contract_as_dict()


# --- Example Usage for Testing the New SCL ---
if __name__ == '__main__':
    import json

    # 1. Simple clock check (Default AFTER)
    contract_str_1 = "dishwashed:loaded AFTER dinner:finished"

    # 2. Clock check (Explicit BEFORE) and Count window
    contract_str_2 = "work:focus AFTER CLOCK(0900) BEFORE AND 2x coffee:brew WITHIN 4h"

    # 3. NOT on Clock (Must be BEFORE 21:00)
    contract_str_3 = "social:out AFTER NOT CLOCK(2100)"

    # 4. NOT on Event (Must not have showered)
    contract_str_4 = "sleep:start AFTER NOT shower:wash"

    # 5. New History Check (Event A SINCE Event B)
    contract_str_5 = "work:complete AFTER code:commit SINCE project:start"

    # 6. Complex Logic (Grouped and mixed)
    contract_str_6 = "task:cleanup AFTER (NOT trash:out AND CLOCK(1800) BETWEEN CLOCK(2000)) OR 1x laundry:load"

    print("--- SCL Parser Examples ---")

    examples = {
        "1. Clock (Default AFTER)": contract_str_1,
        "2. Clock (Explicit BEFORE) & Count": contract_str_2,
        "3. NOT Clock (Must be BEFORE 21:00)": contract_str_3,
        "4. NOT Event (Must not have showered)": contract_str_4,
        "5. History Check (SINCE)": contract_str_5,
        "6. Complex Logic (NOT, Clock Range, OR)": contract_str_6
    }

    for title, dsl in examples.items():
        try:
            result = parse_contract_as_dict(dsl)
            print(f"\n{title}: '{dsl}'")
            print(json.dumps(result, indent=2))
        except ValueError as e:
            print(f"\n{title} FAILED: '{dsl}'")
            print(f"Error: {e}")
