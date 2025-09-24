from gabru.log import Logger
import re


class Lexer:
    def __init__(self):
        self.token_patterns = [
            ('NOT', r'NOT'),
            ('WITHIN', r'WITHIN'),
            ('TIME_UNIT', r's|m|h'),
            ('NUMBER', r'\d+'),
            ('OPERATOR', r'x'),
            ('LOGICAL_OP', r'AND|OR'),
            ('TRIGGER_KEYWORD', r'AFTER'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
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
    if ast_node.type == 'CONTRACT':
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
        condition_dict = ast_to_contract_dict(ast_node.children[0])
        condition_dict["time_window"] = ast_node.value["number"]
        condition_dict["unit"] = ast_node.value["unit"]
        return condition_dict

    if ast_node.type == 'COUNTED_EVENT':
        count = ast_node.value
        event_name = ast_node.children[0].value
        return {
            "type": "event_count",
            "event": event_name,
            "min_count": count
        }

    if ast_node.type == 'EVENT':
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
        self.log = Logger.get_log(self.__class__.__name__)

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None, expected_value=None):
        token = self.current_token()
        if not token:
            raise ValueError("Unexpected end of input.")
        if expected_type and token['type'] != expected_type:
            raise ValueError(f"Expected token of type '{expected_type}', got '{token['type']}'")
        if expected_value and token['value'] != expected_value:
            raise ValueError(f"Expected token value '{expected_value}', got '{token['value']}'")
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

    def parse_term(self):
        token = self.current_token()
        if token['type'] == 'LPAREN':
            self.consume('LPAREN')
            sub_condition_node = self.parse_condition()
            self.consume('RPAREN')
            return sub_condition_node

        if token['type'] == 'NOT':
            self.consume('NOT')
            term_node = self.parse_term()
            return ASTNode('NOT', children=[term_node])

        if token['type'] == 'NUMBER':
            count = int(self.consume('NUMBER')['value'])
            self.consume('OPERATOR', 'x')
            event_node = self.parse_event()
            node = ASTNode('COUNTED_EVENT', value=count, children=[event_node])
        else:
            node = self.parse_event()

        if self.current_token() and self.current_token()['type'] == 'WITHIN':
            duration = self.parse_duration()
            return ASTNode('TEMPORAL_CONDITION', value=duration, children=[node])

        return node

    def parse_condition(self):
        left_node = self.parse_term()
        while self.current_token() and self.current_token()['type'] == 'LOGICAL_OP':
            op_token = self.consume()
            right_node = self.parse_term()
            left_node = ASTNode(op_token['value'], children=[left_node, right_node])
        return left_node

    def parse_contract(self):
        trigger_event_node = self.parse_event()
        self.consume('TRIGGER_KEYWORD', 'AFTER')
        conditions_node = self.parse_condition()
        return ASTNode('CONTRACT', children=[trigger_event_node, conditions_node])

    def parse_contract_as_dict(self):
        ast_node = self.parse_contract()
        return ast_to_contract_dict(ast_node)


lexer = Lexer()


def parse_contract_as_dict(contract_str: str):
    parser = Parser(lexer.tokenize(contract_str))
    return parser.parse_contract_as_dict()


if __name__ == '__main__':
    import json

    # Example usage for the new syntax
    contract_str = "gaming:league_of_legends AFTER (2x exercise WITHIN 1h) AND (laundry:loaded WITHIN 30m)"
    contract_dict = parse_contract_as_dict(contract_str)
    print(json.dumps(contract_dict, indent=2))