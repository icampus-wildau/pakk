import configparser

config_parser = configparser.ConfigParser()
config_parser.add_section("Test")
config_parser.set("Test", "Foo", "Bla")
with open("test.cfg", "w") as f:
    config_parser.write(f)
    
    
from InquirerPy import inquirer

value = inquirer.text(
        message="Message",
        default="default",
        instruction="Instr",
        long_instruction="Long INstr"
        
    ).execute()

print(value)