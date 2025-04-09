import re
import os
import json
from pathlib import Path
import frontmatter
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

class TokenType(Enum):
    AND = 'AND'
    OR = 'OR'
    LPAREN = '('
    RPAREN = ')'
    TAG = 'TAG'

class Token:
    def __init__(self, token_type: TokenType, value: str = None):
        self.token_type = token_type
        self.value = value

    def __str__(self):
        return f"{self.token_type.name}({self.value})" if self.value else self.token_type.name

class FilterTokenType(Enum):
    FIELD = 'FIELD'      # price, location 등
    OPERATOR = 'OPERATOR'  # >, <, =, >=, <=
    VALUE = 'VALUE'      # "$$$", "main island" 등

class FilterToken:
    def __init__(self, token_type: FilterTokenType, value: str):
        self.token_type = token_type
        self.value = value

    def __str__(self):
        return f"{self.token_type.name}({self.value})"

class QueryParser:
    def tokenize(self, expr: str) -> List[Token]:
        """Convert expression string into tokens"""
        tokens = []
        current = ''
        i = 0
        
        while i < len(expr):
            char = expr[i]
            
            # Handle quoted strings
            if char == '"':
                if current:
                    tokens.append(Token(TokenType.TAG, current.strip()))
                    current = ''
                i += 1  # Skip opening quote
                while i < len(expr) and expr[i] != '"':
                    current += expr[i]
                    i += 1
                i += 1  # Skip closing quote
                if current:
                    tokens.append(Token(TokenType.TAG, current.strip()))
                    current = ''
                continue
            
            # Handle parentheses
            elif char == '(':
                if current:
                    tokens.append(Token(TokenType.TAG, current.strip()))
                    current = ''
                tokens.append(Token(TokenType.LPAREN))
            elif char == ')':
                if current:
                    tokens.append(Token(TokenType.TAG, current.strip()))
                    current = ''
                tokens.append(Token(TokenType.RPAREN))
            
            # Handle operators
            elif char.isspace():
                if current:
                    if current == 'AND':
                        tokens.append(Token(TokenType.AND))
                    elif current == 'OR':
                        tokens.append(Token(TokenType.OR))
                    else:
                        tokens.append(Token(TokenType.TAG, current.strip()))
                    current = ''
            else:
                current += char
            
            i += 1
        
        # Handle any remaining token
        if current:
            if current == 'AND':
                tokens.append(Token(TokenType.AND))
            elif current == 'OR':
                tokens.append(Token(TokenType.OR))
            else:
                tokens.append(Token(TokenType.TAG, current.strip()))
        
        return tokens

    def parse_expression(self, tokens: List[Token], start: int) -> Tuple[Dict[str, Any], int]:
        """Parse a single expression from tokens"""
        if start >= len(tokens):
            return {'type': 'empty'}, start

        left = {'type': 'empty'}  # Initialize left with empty node
        i = start

        # Parse single tag or parenthesized expression
        if tokens[i].token_type == TokenType.TAG:
            left = {'type': 'tag', 'value': tokens[i].value}
            i += 1
        elif tokens[i].token_type == TokenType.LPAREN:
            i += 1
            left, i = self.parse_expression(tokens, i)
            if i < len(tokens) and tokens[i].token_type == TokenType.RPAREN:
                i += 1
            else:
                raise ValueError("Missing closing parenthesis")

        # If we have an operator following, parse the right side
        while i < len(tokens) and (tokens[i].token_type == TokenType.AND or tokens[i].token_type == TokenType.OR):
            operator = tokens[i].token_type.value
            i += 1
            right, i = self.parse_expression(tokens, i)
            left = {
                'type': 'operator',
                'operator': operator,
                'left': left,
                'right': right
            }

        return left, i

    def build_ast(self, tokens: List[Token]) -> dict:
        """Build an Abstract Syntax Tree from tokens"""
        ast, _ = self.parse_expression(tokens, 0)
        if not isinstance(ast, dict):
            return {'type': 'empty'}
        return ast

    def evaluate_ast(self, ast: dict, tags: List[str]) -> bool:
        """Evaluate the AST against a list of tags"""
        if not ast or not isinstance(ast, dict):
            return False

        if ast['type'] == 'empty':
            return True

        if ast['type'] == 'tag':
            return ast['value'] in tags

        if ast['type'] == 'operator':
            left = self.evaluate_ast(ast['left'], tags)
            right = self.evaluate_ast(ast['right'], tags)
            
            if ast['operator'] == 'AND':
                return left and right
            elif ast['operator'] == 'OR':
                return left or right

        return False

    def parse_tags_expression(self, expr: str) -> dict:
        """Parse tag expressions like: (luxury AND "bora bora") OR beachfront"""
        tokens = self.tokenize(expr)
        ast = self.build_ast(tokens)
        if not isinstance(ast, dict):
            return {'type': 'tag', 'value': expr}
        return ast

    def tokenize_filter(self, expr: str) -> List[FilterToken]:
        """Convert filter expression string into tokens"""
        tokens = []
        expr = expr.strip()
        
        # Split into parts (field, operator, value)
        parts = re.split(r'(\s*[<>=]+\s*)', expr)
        if len(parts) != 3:
            raise ValueError(f"Invalid filter expression: {expr}")
        
        field, operator, value = [p.strip() for p in parts]
        
        # Add field token
        tokens.append(FilterToken(FilterTokenType.FIELD, field))
        
        # Add operator token
        tokens.append(FilterToken(FilterTokenType.OPERATOR, operator))
        
        # Add value token (strip quotes if present)
        value = value.strip('"\'')
        tokens.append(FilterToken(FilterTokenType.VALUE, value))
        
        return tokens

    def parse_filter_expression(self, expr: str) -> dict:
        """Parse filter expressions like: price > "$$$" """
        tokens = self.tokenize_filter(expr)
        
        return {
            'type': 'filter',
            'field': tokens[0].value,
            'operator': tokens[1].value,
            'value': tokens[2].value
        }

    def evaluate_filter(self, filter_ast: dict, item_data: dict) -> bool:
        """Evaluate a filter against item data"""
        if not filter_ast or filter_ast['type'] != 'filter':
            return True
            
        field = filter_ast['field']
        operator = filter_ast['operator']
        filter_value = filter_ast['value']
        
        if field not in item_data:
            return False
            
        item_value = item_data[field]
        
        # Special handling for price comparison with $ symbols
        if field == 'price' and isinstance(filter_value, str) and '$' in filter_value:
            # Convert $$ notation to number
            filter_level = filter_value.count('$')
            item_level = item_value.count('$') if isinstance(item_value, str) else 0
            
            if operator == '>':
                return item_level > filter_level
            elif operator == '<':
                return item_level < filter_level
            elif operator == '>=':
                return item_level >= filter_level
            elif operator == '<=':
                return item_level <= filter_level
            elif operator == '=':
                return item_level == filter_level
        
        # Regular comparison
        if operator == '>':
            return item_value > filter_value
        elif operator == '<':
            return item_value < filter_value
        elif operator == '>=':
            return item_value >= filter_value
        elif operator == '<=':
            return item_value <= filter_value
        elif operator == '=':
            return item_value == filter_value
            
        return False

class EmbedProcessor:
    def __init__(self, content_root: Path):
        self.content_root = content_root
        self.query_parser = QueryParser()

    def clean_generated_folders(self):
        """Remove all _generated folders in the content directory"""
        for generated_folder in self.content_root.rglob("_generated"):
            if generated_folder.is_dir():
                relative_path = generated_folder.relative_to(self.content_root.parent)
                print(f"Removing generated folder: {relative_path}")
                # Remove all files in the directory
                for file in generated_folder.glob("*"):
                    file.unlink()
                # Remove the directory itself
                generated_folder.rmdir()

    def process_file(self, file_path: Path):
        """Process a single markdown file"""
        relative_path = file_path.relative_to(self.content_root.parent)
        print(f"Processing file: {relative_path}")
        
        # Clean any existing generated folders first
        self.clean_generated_folders()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all embed commands
        embed_pattern = r'@embed\s+\w+\s*{[^}]*}'
        commands = re.finditer(embed_pattern, content, re.DOTALL)
        
        # Process each command
        for match in commands:
            command = match.group()
            try:
                parsed = self.parse_embed_command(command)
                generated_content = self.generate_content(parsed, file_path)
                
                # Create _generated directory if it doesn't exist
                generated_dir = file_path.parent / '_generated'
                generated_dir.mkdir(exist_ok=True)
                
                # Write generated content
                output_file = generated_dir / f"{parsed['params']['output']}.md"
                relative_output = output_file.relative_to(self.content_root.parent)
                output_file.write_text(generated_content)
                
                print(f"Generated: {relative_output}")
                
            except Exception as e:
                print(f"Error processing command {command}: {e}")

    def parse_embed_command(self, command: str) -> Dict[str, Any]:
        """
        Parse embed command string into structured data
        Example input:
        @embed hotels {
            output: "luxury-hotels",
            tags: (luxury AND "bora bora"),
            filter: price > "$$$",
            sort: price DESC,
            view: interactive
        }
        """
        # Extract command parameters using regex
        pattern = r'@embed\s+(\w+)\s*{([^}]*)}'
        match = re.match(pattern, command, re.DOTALL)
        if not match:
            raise ValueError("Invalid embed command format")

        content_type, params_str = match.groups()
        
        # Parse parameters
        params = {}
        for line in params_str.strip().split('\n'):
            line = line.strip().strip(',')
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                params[key] = value

        return {
            'type': str(content_type),
            'params': params
        }

    def generate_content(self, parsed_command: Dict[str, Any], source_file: Path) -> str:
        """Generate content based on parsed command"""
        if not isinstance(parsed_command, dict):
            raise ValueError(f"Expected dict, got {type(parsed_command)}")
            
        if 'type' not in parsed_command:
            raise ValueError("Missing 'type' in parsed command")
            
        if parsed_command['type'] == 'hotels':
            return self.generate_hotels_content(parsed_command['params'])
        # Add other content types here
        raise ValueError(f"Unknown content type: {parsed_command['type']}")

    def load_hotel_data(self) -> List[Dict[str, Any]]:
        """Load all hotel data from markdown files"""
        hotels = []
        hotels_dir = self.content_root / 'hotels'
        
        for md_file in hotels_dir.glob('*.md'):
            try:
                # Parse frontmatter and content
                post = frontmatter.load(md_file)
                
                # Extract hotel name from H3 header
                content_lines = post.content.split('\n')
                hotel_name = next((line.strip('# ') for line in content_lines 
                                 if line.startswith('### ')), '')
                
                # Parse metadata from content (location, price, etc)
                metadata = {}
                for line in content_lines:
                    if line.startswith('- **') and ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip('- *')
                        metadata[key.lower()] = value.strip()
                
                hotels.append({
                    'name': hotel_name,
                    'tags': post.get('tags', []),
                    'content': post.content,
                    **metadata
                })
                
            except Exception as e:
                print(f"Error loading hotel {md_file}: {e}")
                
        return hotels

    def sort_hotels(self, hotels: List[Dict], sort_expr: str) -> List[Dict]:
        """Sort hotels based on expression like 'price DESC'"""
        if not sort_expr:
            return hotels
            
        parts = sort_expr.split()
        if len(parts) != 2:
            return hotels
            
        field, direction = parts
        
        reverse = direction.upper() == 'DESC'
        
        def sort_key(hotel):
            value = hotel.get(field.lower(), '')
            if field.lower() == 'price':
                # Sort by number of $ symbols
                return value.count('$') if isinstance(value, str) else 0
            return value
            
        return sorted(hotels, key=sort_key, reverse=reverse)

    def generate_hotels_content(self, params: Dict[str, Any]) -> str:
        """Generate hotels content based on parameters"""
        # Load all hotel data
        hotels = self.load_hotel_data()
        
        # Apply tag filtering if specified
        if 'tags' in params:
            tags_ast = self.query_parser.parse_tags_expression(params['tags'])
            hotels = [
                hotel for hotel in hotels 
                if self.query_parser.evaluate_ast(tags_ast, hotel['tags'])
            ]
        
        # Apply additional filtering if specified
        if 'filter' in params:
            filter_ast = self.query_parser.parse_filter_expression(params['filter'])
            hotels = [
                hotel for hotel in hotels 
                if self.query_parser.evaluate_filter(filter_ast, hotel)
            ]
        
        # Apply sorting if specified
        if 'sort' in params:
            hotels = self.sort_hotels(hotels, params['sort'])
        
        # Generate output
        if not hotels:
            return "No hotels found matching the criteria."
        
        # Check if interactive view is requested
        is_interactive = params.get('view', '').lower() == 'interactive'
        
        # Generate content
        output = []
        for hotel in hotels:
            if is_interactive:
                # Add data attributes for interactive filtering/sorting
                price_level = hotel.get('price', '').count('$')
                output.append(f'''<div class="hotel-card" 
                    data-price-level="{price_level}"
                    data-tags="{','.join(hotel.get('tags', []))}"
                >''')
                
            output.append(hotel.get('content', '').strip())
            
            if is_interactive:
                output.append('</div>')
            
            output.append('\n---\n')  # Separator between hotels
        
        return '\n'.join(output)

def main():
    # Get the project root directory (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    content_root = project_root / "contents"
    
    print(f"Project root: {project_root}")
    print(f"Content root: {content_root}")
    
    processor = EmbedProcessor(content_root)
    
    # Process all markdown files in destinations
    destinations_dir = content_root / "destinations"
    print(f"Looking for markdown files in: {destinations_dir.relative_to(project_root)}")
    
    for md_file in destinations_dir.rglob("*.md"):
        relative_path = md_file.relative_to(project_root)
        print(f"Found markdown file: {relative_path}")
        if not md_file.parent.name == "_generated":  # Skip generated files
            print(f"Processing file: {relative_path}")
            processor.process_file(md_file)

if __name__ == "__main__":
    main() 