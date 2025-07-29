

from pakk.pakkage.core import PakkageConfig




class PakkCliOptionsParser:
    """
    Parser for [run_options] section in pakk.cfg.
    Maps CLI options to environment variables.
    
    Supports three approaches:
    1. Simple assignment in pakk.cfg: 
    ```
    [run_options]
    -d = MICROPHONE_DEVICE_NAME
    ```
    
    2. Detailed options in pakk.cfg:
    ```
    [run_options]
    device = {type: str, env: MICROPHONE_DEVICE_NAME, help: "Device name"}
    ```
    
    3. Dynamic env vars:
    ```
    pakk run --env-MICROPHONE_DEVICE_NAME=value
    ```
    """
    
    PAKK_SECTION_NAME = "run_options"
    
    def __init__(self, pakkage_version: PakkageConfig):
        self.pakkage_version = pakkage_version
        self.env_mappings: dict[str, str] = {}
        
        self.parse_cfg_file()
        
    def parse_cfg_file(self):
        cfg = self.pakkage_version.cfg
        
        if not cfg.has_section(self.PAKK_SECTION_NAME):
            return
        
        options = cfg.options(self.PAKK_SECTION_NAME)
        for option in options:
            if option.startswith('-'):
                self.env_mappings[option] = cfg.get(self.PAKK_SECTION_NAME, option)
        
        print("--------------------------------")
        print("ENV MAPPINGS")
        print(self.env_mappings)
        
    
    def parse_cli_options(self, option_list: list[str]):
        pass
        
        
        
        
    #     def parse_run_options(self, instruction_content: str):
    #     """Parse the run_options section content"""
    #     # This will be called for each line in the [RunOptions] section
    #     # The instruction_content will be the full section content
    #     lines = instruction_content.strip().split('\n')
        
    #     for line in lines:
    #         line = line.strip()
    #         if not line or line.startswith('#'):
    #             continue
                
    #         if '=' in line:
    #             key, value = line.split('=', 1)
    #             key = key.strip()
    #             value = value.strip()
                
    #             # Approach 1: Simple assignment
    #             if key.startswith('-') and not value.startswith('{'):
    #                 self.simple_mappings[key] = value
                    
    #             # Approach 2: Dynamic options
    #             elif value.startswith('{') and value.endswith('}'):
    #                 try:
    #                     # Simple JSON-like parsing for the dynamic options
    #                     import ast
    #                     option_config = ast.literal_eval(value)
    #                     self.dynamic_options[key] = option_config
    #                 except:
    #                     # Fallback to simple assignment if parsing fails
    #                     self.simple_mappings[key] = value
                        
    #             # Approach 3: Direct environment variable assignment
    #             elif key.startswith('--env-'):
    #                 env_var = key[6:]  # Remove '--env-' prefix
    #                 self.simple_mappings[f"--env-{env_var}"] = env_var
                    
    #             else:
    #                 # Default to simple assignment
    #                 self.simple_mappings[key] = value
                    
    # def get_cli_to_env_mapping(self) -> dict[str, str]:
    #     """Get the complete CLI to environment variable mapping"""
    #     mapping = self.simple_mappings.copy()
        
    #     # Add dynamic options to the mapping
    #     for option, config in self.dynamic_options.items():
    #         if 'env' in config:
    #             mapping[option] = config['env']
                
    #     return mapping
        
    # def get_dynamic_options_config(self) -> dict[str, dict]:
    #     """Get the dynamic options configuration for Click"""
    #     return self.dynamic_options.copy()







# def parse_run_arguments(run_args: list[str], pakkage_config) -> dict[str, str]:
#     """
#     Parse run arguments and convert them to environment variables.
    
#     Supports three approaches:
#     1. Simple assignment from pakk.cfg: -d=value -> MICROPHONE_DEVICE_NAME=value
#     2. Dynamic options: --device=value -> MICROPHONE_DEVICE_NAME=value  
#     3. Arbitrary env vars: --env-MICROPHONE_DEVICE_NAME=value -> MICROPHONE_DEVICE_NAME=value
#     """
#     env_vars = {}
    
#     if not run_args:
#         return env_vars
        
#     # Get CLI to environment variable mappings from the package
#     cli_to_env_mapping = {}
#     dynamic_options_config = {}
    
#     # Check if the package has RunOptions type
#     for type_instance in pakkage_config.pakk_types:
#         if hasattr(type_instance, 'get_cli_to_env_mapping'):
#             cli_to_env_mapping.update(type_instance.get_cli_to_env_mapping())
#             if hasattr(type_instance, 'get_dynamic_options_config'):
#                 dynamic_options_config.update(type_instance.get_dynamic_options_config())
    
#     for arg in run_args:
#         if '=' in arg:
#             option, value = arg.split('=', 1)
#             option = option.strip()
#             value = value.strip().strip('"\'')
            
#             # Approach 1 & 2: Use mappings from pakk.cfg
#             if option in cli_to_env_mapping:
#                 env_var = cli_to_env_mapping[option]
#                 env_vars[env_var] = value
                
#             # Approach 3: Arbitrary environment variables with --env- prefix
#             elif option.startswith('--env-'):
#                 env_var = option[6:]  # Remove '--env-' prefix
#                 env_vars[env_var] = value
                
#     return env_vars