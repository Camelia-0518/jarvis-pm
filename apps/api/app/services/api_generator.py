"""
API接口生成器
从PRD数据需求提取数据模型，生成OpenAPI 3.0规范和CRUD接口
"""

import re
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class DataType(Enum):
    """数据类型"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "date-time"
    EMAIL = "email"
    UUID = "uuid"


class HTTPMethod(Enum):
    """HTTP方法"""
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


@dataclass
class APIField:
    """API字段定义"""
    name: str
    type: DataType
    description: str = ""
    required: bool = False
    nullable: bool = False
    default: Any = None
    example: Any = None
    enum: List[str] = field(default_factory=list)
    format: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    ref: Optional[str] = None  # 引用其他Schema


@dataclass
class APISchema:
    """API Schema定义"""
    name: str
    description: str = ""
    fields: List[APIField] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)


@dataclass
class APIParameter:
    """API参数定义"""
    name: str
    location: str  # query, path, header, cookie
    type: DataType
    description: str = ""
    required: bool = False
    default: Any = None
    example: Any = None


@dataclass
class APIResponse:
    """API响应定义"""
    status_code: int
    description: str
    schema_ref: Optional[str] = None
    content_type: str = "application/json"
    example: Optional[Dict] = None


@dataclass
class APIEndpoint:
    """API端点定义"""
    path: str
    method: HTTPMethod
    summary: str
    description: str = ""
    operation_id: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[APIParameter] = field(default_factory=list)
    request_body: Optional[Dict] = None
    responses: List[APIResponse] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class APIDocument:
    """API文档定义"""
    title: str
    version: str
    description: str = ""
    servers: List[Dict[str, str]] = field(default_factory=list)
    schemas: List[APISchema] = field(default_factory=list)
    endpoints: List[APIEndpoint] = field(default_factory=list)
    security_schemes: Dict[str, Dict] = field(default_factory=dict)
    tags: List[Dict[str, str]] = field(default_factory=list)


class PRDDataExtractor:
    """PRD数据需求提取器"""

    # 数据模型识别模式
    MODEL_PATTERNS = [
        r'(?:数据|实体|模型)[：:]\s*([^\n]+)',
        r'(?:Data|Entity|Model)[：:]\s*([^\n]+)',
        r'###\s*([^\n]+?)(?:数据|实体|模型)',
        r'\*\*([^\*]+?)\*\*\s*(?:表|实体)',
    ]

    # 字段识别模式
    FIELD_PATTERNS = [
        r'[-*]\s*([^：:\(\[\n]+)[：:]\s*([^\n]+)',
        r'\|\s*([^\|]+)\|\s*([^\|]+)\|',
        r'([^，,\s]+)[,，]\s*(字符串|整数|数字|布尔|日期|数组|对象)',
    ]

    # 数据类型映射
    TYPE_MAPPING = {
        # 中文类型
        '字符串': DataType.STRING,
        '文本': DataType.STRING,
        '文字': DataType.STRING,
        '整数': DataType.INTEGER,
        '整型': DataType.INTEGER,
        '数字': DataType.NUMBER,
        '数值': DataType.NUMBER,
        '浮点数': DataType.NUMBER,
        '布尔': DataType.BOOLEAN,
        '布尔值': DataType.BOOLEAN,
        '日期': DataType.DATE,
        '日期时间': DataType.DATETIME,
        '时间': DataType.DATETIME,
        '数组': DataType.ARRAY,
        '列表': DataType.ARRAY,
        '对象': DataType.OBJECT,
        '邮箱': DataType.EMAIL,
        '邮件': DataType.EMAIL,
        'UUID': DataType.UUID,
        'ID': DataType.UUID,
        # 英文类型
        'string': DataType.STRING,
        'int': DataType.INTEGER,
        'integer': DataType.INTEGER,
        'number': DataType.NUMBER,
        'float': DataType.NUMBER,
        'double': DataType.NUMBER,
        'bool': DataType.BOOLEAN,
        'boolean': DataType.BOOLEAN,
        'date': DataType.DATE,
        'datetime': DataType.DATETIME,
        'array': DataType.ARRAY,
        'list': DataType.ARRAY,
        'object': DataType.OBJECT,
        'email': DataType.EMAIL,
        'uuid': DataType.UUID,
    }

    # API操作识别模式
    API_PATTERNS = {
        'list': [
            r'(?:获取|查询|列出|列表).*?(?:列表|数据|全部|所有)',
            r'(?:list|get|query|search|find)\s+all',
            r'GET\s+/[^/\s]+/?\s*$',
        ],
        'create': [
            r'(?:创建|新增|添加|插入).*?(?:数据|记录)',
            r'(?:create|add|insert|new)',
            r'POST\s+/[^/\s]+/?\s*$',
        ],
        'retrieve': [
            r'(?:获取|查询|查看|详情).*?(?:详情|单个|具体)',
            r'(?:get|retrieve|detail|view)\s+(?:by\s+id|detail)',
            r'GET\s+/[^/\s]+/\{[^}]+\}',
        ],
        'update': [
            r'(?:更新|修改|编辑).*?(?:数据|记录)',
            r'(?:update|modify|edit|change)',
            r'PUT|PATCH\s+/[^/\s]+/\{[^}]+\}',
        ],
        'delete': [
            r'(?:删除|移除).*?(?:数据|记录)',
            r'(?:delete|remove|destroy)',
            r'DELETE\s+/[^/\s]+/\{[^}]+\}',
        ],
    }

    def __init__(self, prd_content: str):
        self.prd_content = prd_content
        self.lines = prd_content.split('\n')

    def extract(self) -> APIDocument:
        """提取API文档"""
        # 提取基本信息
        title = self._extract_title()
        description = self._extract_description()

        # 提取数据模型
        schemas = self._extract_schemas()

        # 提取API端点
        endpoints = self._extract_endpoints(schemas)

        return APIDocument(
            title=title,
            version="1.0.0",
            description=description,
            servers=[
                {"url": "http://localhost:8000", "description": "本地开发环境"},
                {"url": "https://api.example.com", "description": "生产环境"},
            ],
            schemas=schemas,
            endpoints=endpoints,
            security_schemes={
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                },
            },
            tags=[
                {"name": schema.name, "description": f"{schema.name}相关操作"}
                for schema in schemas
            ],
        )

    def _extract_title(self) -> str:
        """提取API标题"""
        patterns = [
            r'^#\s*([^\n]+)',
            r'API[：:]\s*([^\n]+)',
            r'接口[：:]\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.prd_content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "API"

    def _extract_description(self) -> str:
        """提取API描述"""
        patterns = [
            r'API描述[：:]\s*([^#]+)',
            r'接口描述[：:]\s*([^#]+)',
            r'##\s*描述\s*\n([^#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.prd_content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_schemas(self) -> List[APISchema]:
        """提取数据模型"""
        schemas = []

        # 查找数据模型区块
        model_sections = self._find_model_sections()

        for section_name, section_content in model_sections:
            schema = self._parse_schema(section_name, section_content)
            if schema:
                schemas.append(schema)

        # 如果没有找到模型，创建默认模型
        if not schemas:
            schemas = self._create_default_schemas()

        return schemas

    def _find_model_sections(self) -> List[tuple]:
        """查找数据模型区块"""
        sections = []

        # 查找模型标题
        for i, line in enumerate(self.lines):
            for pattern in self.MODEL_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    model_name = match.group(1).strip() if match.groups() else line.strip('# *')

                    # 查找区块结束位置
                    end_idx = len(self.lines)
                    for j in range(i + 1, len(self.lines)):
                        if re.match(r'^#{2,4}\s+', self.lines[j]):
                            end_idx = j
                            break

                    content = '\n'.join(self.lines[i:end_idx])
                    sections.append((model_name, content))
                    break

        return sections

    def _parse_schema(self, name: str, content: str) -> Optional[APISchema]:
        """解析单个数据模型"""
        fields = []
        required_fields = []

        # 提取字段定义
        for pattern in self.FIELD_PATTERNS:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                field_name = match.group(1).strip()
                field_desc = match.group(2).strip() if match.lastindex >= 2 else ""

                # 解析字段类型
                field_type = self._parse_field_type(field_desc)

                # 检查是否必填
                is_required = self._check_required(field_desc, field_name)

                # 解析约束
                constraints = self._parse_constraints(field_desc)

                field = APIField(
                    name=field_name,
                    type=field_type,
                    description=field_desc.split('，')[0].split(',')[0],
                    required=is_required,
                    **constraints
                )
                fields.append(field)

                if is_required:
                    required_fields.append(field_name)

        # 添加标准字段
        fields.extend(self._get_standard_fields())

        return APISchema(
            name=self._normalize_schema_name(name),
            description=f"{name}数据模型",
            fields=fields,
            required_fields=required_fields
        )

    def _parse_field_type(self, description: str) -> DataType:
        """解析字段类型"""
        # 查找类型关键词
        for type_keyword, data_type in self.TYPE_MAPPING.items():
            if type_keyword in description.lower():
                return data_type

        # 根据字段名推断类型
        if any(keyword in description for keyword in ['ID', 'id', '编号', '数量', '次数', '年龄']):
            return DataType.INTEGER
        elif any(keyword in description for keyword in ['时间', '日期', 'date', 'time']):
            return DataType.DATETIME
        elif any(keyword in description for keyword in ['邮箱', 'email', '邮件']):
            return DataType.EMAIL
        elif any(keyword in description for keyword in ['是否', '状态', '启用', '激活', '布尔']):
            return DataType.BOOLEAN
        elif any(keyword in description for keyword in ['列表', '数组', '多个', 'array', 'list']):
            return DataType.ARRAY

        return DataType.STRING

    def _check_required(self, description: str, field_name: str) -> bool:
        """检查字段是否必填"""
        required_keywords = ['必填', '必需', 'required', '必须', '不可为空', 'not null', '*']
        if any(kw in description for kw in required_keywords):
            return True

        # ID字段通常必填
        if field_name.lower() in ['id', 'uuid', '编号']:
            return True

        return False

    def _parse_constraints(self, description: str) -> Dict[str, Any]:
        """解析字段约束"""
        constraints = {}

        # 长度限制
        length_match = re.search(r'(\d+)\s*[-~]\s*(\d+)\s*(?:字符|字|长度|长度)', description)
        if length_match:
            constraints['min_length'] = int(length_match.group(1))
            constraints['max_length'] = int(length_match.group(2))
        else:
            max_match = re.search(r'(?:最多|最大|不超过|小于等于|<=)\s*(\d+)\s*(?:字符|字)', description)
            if max_match:
                constraints['max_length'] = int(max_match.group(1))

            min_match = re.search(r'(?:最少|最小|至少|大于等于|>=)\s*(\d+)\s*(?:字符|字)', description)
            if min_match:
                constraints['min_length'] = int(min_match.group(1))

        # 数值范围
        range_match = re.search(r'(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)', description)
        if range_match:
            constraints['minimum'] = float(range_match.group(1))
            constraints['maximum'] = float(range_match.group(2))

        # 枚举值
        enum_match = re.search(r'(?:枚举|选项|可选值|包括)[：:]\s*([^\n]+)', description)
        if enum_match:
            enum_values = re.split(r'[,，、/|]', enum_match.group(1))
            constraints['enum'] = [v.strip() for v in enum_values if v.strip()]

        # 正则模式
        pattern_match = re.search(r'(?:格式|模式|正则)[：:]\s*([^\n]+)', description)
        if pattern_match:
            constraints['pattern'] = pattern_match.group(1).strip()

        # 示例值
        example_match = re.search(r'(?:示例|例子|如|例如)[：:]\s*([^\n，,]+)', description)
        if example_match:
            constraints['example'] = example_match.group(1).strip()

        return constraints

    def _get_standard_fields(self) -> List[APIField]:
        """获取标准字段（创建时间、更新时间等）"""
        return [
            APIField(
                name="id",
                type=DataType.UUID,
                description="唯一标识符",
                required=True,
                example="550e8400-e29b-41d4-a716-446655440000"
            ),
            APIField(
                name="created_at",
                type=DataType.DATETIME,
                description="创建时间",
                required=True,
                example="2024-01-01T00:00:00Z"
            ),
            APIField(
                name="updated_at",
                type=DataType.DATETIME,
                description="更新时间",
                required=True,
                example="2024-01-01T00:00:00Z"
            ),
        ]

    def _normalize_schema_name(self, name: str) -> str:
        """规范化Schema名称"""
        # 移除常见后缀
        name = re.sub(r'(?:数据|实体|模型|表|Table|Entity|Model)$', '', name, flags=re.IGNORECASE)
        # 转换为PascalCase
        words = re.split(r'[-_\s]+', name.strip())
        return ''.join(word.capitalize() for word in words if word)

    def _create_default_schemas(self) -> List[APISchema]:
        """创建默认数据模型"""
        return [
            APISchema(
                name="Item",
                description="通用数据项",
                fields=[
                    APIField(name="id", type=DataType.UUID, description="唯一标识", required=True),
                    APIField(name="name", type=DataType.STRING, description="名称", required=True, max_length=100),
                    APIField(name="description", type=DataType.STRING, description="描述", max_length=500),
                    APIField(name="status", type=DataType.STRING, description="状态", enum=["active", "inactive"]),
                    APIField(name="created_at", type=DataType.DATETIME, description="创建时间", required=True),
                    APIField(name="updated_at", type=DataType.DATETIME, description="更新时间", required=True),
                ],
                required_fields=["id", "name", "created_at", "updated_at"]
            )
        ]

    def _extract_endpoints(self, schemas: List[APISchema]) -> List[APIEndpoint]:
        """提取API端点"""
        endpoints = []

        for schema in schemas:
            # 为每个Schema生成CRUD端点
            base_path = f"/{self._to_kebab_case(schema.name)}"

            # List - GET /
            endpoints.append(APIEndpoint(
                path=base_path,
                method=HTTPMethod.GET,
                summary=f"获取{schema.name}列表",
                description=f"分页获取{schema.name}列表，支持筛选和排序",
                operation_id=f"list_{self._to_snake_case(schema.name)}s",
                tags=[schema.name],
                parameters=self._get_list_parameters(),
                responses=[
                    APIResponse(
                        status_code=200,
                        description="成功获取列表",
                        schema_ref=f"{schema.name}ListResponse",
                    ),
                    APIResponse(status_code=400, description="请求参数错误"),
                    APIResponse(status_code=401, description="未授权"),
                ],
                security=["bearerAuth"],
            ))

            # Create - POST /
            endpoints.append(APIEndpoint(
                path=base_path,
                method=HTTPMethod.POST,
                summary=f"创建{schema.name}",
                description=f"创建新的{schema.name}记录",
                operation_id=f"create_{self._to_snake_case(schema.name)}",
                tags=[schema.name],
                request_body={
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema.name}Create"}
                        }
                    },
                    "required": True,
                },
                responses=[
                    APIResponse(
                        status_code=201,
                        description="创建成功",
                        schema_ref=schema.name,
                    ),
                    APIResponse(status_code=400, description="请求数据验证失败"),
                    APIResponse(status_code=401, description="未授权"),
                    APIResponse(status_code=409, description="资源已存在"),
                ],
                security=["bearerAuth"],
            ))

            # Retrieve - GET /{id}
            endpoints.append(APIEndpoint(
                path=f"{base_path}/{{id}}",
                method=HTTPMethod.GET,
                summary=f"获取{schema.name}详情",
                description=f"根据ID获取{schema.name}详细信息",
                operation_id=f"get_{self._to_snake_case(schema.name)}",
                tags=[schema.name],
                parameters=[
                    APIParameter(
                        name="id",
                        location="path",
                        type=DataType.UUID,
                        description="资源ID",
                        required=True,
                    ),
                ],
                responses=[
                    APIResponse(
                        status_code=200,
                        description="成功获取详情",
                        schema_ref=schema.name,
                    ),
                    APIResponse(status_code=404, description="资源不存在"),
                ],
                security=["bearerAuth"],
            ))

            # Update - PUT /{id}
            endpoints.append(APIEndpoint(
                path=f"{base_path}/{{id}}",
                method=HTTPMethod.PUT,
                summary=f"更新{schema.name}",
                description=f"完整更新{schema.name}信息",
                operation_id=f"update_{self._to_snake_case(schema.name)}",
                tags=[schema.name],
                parameters=[
                    APIParameter(
                        name="id",
                        location="path",
                        type=DataType.UUID,
                        description="资源ID",
                        required=True,
                    ),
                ],
                request_body={
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema.name}Update"}
                        }
                    },
                    "required": True,
                },
                responses=[
                    APIResponse(
                        status_code=200,
                        description="更新成功",
                        schema_ref=schema.name,
                    ),
                    APIResponse(status_code=400, description="请求数据验证失败"),
                    APIResponse(status_code=404, description="资源不存在"),
                ],
                security=["bearerAuth"],
            ))

            # Partial Update - PATCH /{id}
            endpoints.append(APIEndpoint(
                path=f"{base_path}/{{id}}",
                method=HTTPMethod.PATCH,
                summary=f"部分更新{schema.name}",
                description=f"部分更新{schema.name}信息",
                operation_id=f"partial_update_{self._to_snake_case(schema.name)}",
                tags=[schema.name],
                parameters=[
                    APIParameter(
                        name="id",
                        location="path",
                        type=DataType.UUID,
                        description="资源ID",
                        required=True,
                    ),
                ],
                request_body={
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema.name}PartialUpdate"}
                        }
                    },
                    "required": True,
                },
                responses=[
                    APIResponse(
                        status_code=200,
                        description="更新成功",
                        schema_ref=schema.name,
                    ),
                    APIResponse(status_code=400, description="请求数据验证失败"),
                    APIResponse(status_code=404, description="资源不存在"),
                ],
                security=["bearerAuth"],
            ))

            # Delete - DELETE /{id}
            endpoints.append(APIEndpoint(
                path=f"{base_path}/{{id}}",
                method=HTTPMethod.DELETE,
                summary=f"删除{schema.name}",
                description=f"删除指定的{schema.name}记录",
                operation_id=f"delete_{self._to_snake_case(schema.name)}",
                tags=[schema.name],
                parameters=[
                    APIParameter(
                        name="id",
                        location="path",
                        type=DataType.UUID,
                        description="资源ID",
                        required=True,
                    ),
                ],
                responses=[
                    APIResponse(status_code=204, description="删除成功"),
                    APIResponse(status_code=404, description="资源不存在"),
                ],
                security=["bearerAuth"],
            ))

        return endpoints

    def _get_list_parameters(self) -> List[APIParameter]:
        """获取列表查询参数"""
        return [
            APIParameter(
                name="page",
                location="query",
                type=DataType.INTEGER,
                description="页码",
                default=1,
                example=1,
            ),
            APIParameter(
                name="page_size",
                location="query",
                type=DataType.INTEGER,
                description="每页数量",
                default=20,
                example=20,
            ),
            APIParameter(
                name="sort",
                location="query",
                type=DataType.STRING,
                description="排序字段",
                example="-created_at",
            ),
            APIParameter(
                name="search",
                location="query",
                type=DataType.STRING,
                description="搜索关键词",
            ),
        ]

    def _to_kebab_case(self, name: str) -> str:
        """转换为kebab-case"""
        # PascalCase to kebab-case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

    def _to_snake_case(self, name: str) -> str:
        """转换为snake_case"""
        return self._to_kebab_case(name).replace('-', '_')


class OpenAPIGenerator:
    """OpenAPI 3.0规范生成器"""

    def __init__(self, api_doc: APIDocument):
        self.api_doc = api_doc

    def generate(self) -> Dict[str, Any]:
        """生成OpenAPI 3.0规范"""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.api_doc.title,
                "description": self.api_doc.description,
                "version": self.api_doc.version,
                "contact": {
                    "name": "API Support",
                    "email": "api@example.com",
                },
            },
            "servers": self.api_doc.servers,
            "paths": self._generate_paths(),
            "components": {
                "schemas": self._generate_schemas(),
                "securitySchemes": self.api_doc.security_schemes,
                "responses": self._generate_common_responses(),
            },
            "tags": self.api_doc.tags,
        }

        return spec

    def _generate_paths(self) -> Dict[str, Any]:
        """生成路径定义"""
        paths = {}

        for endpoint in self.api_doc.endpoints:
            if endpoint.path not in paths:
                paths[endpoint.path] = {}

            paths[endpoint.path][endpoint.method.value] = self._generate_operation(endpoint)

        return paths

    def _generate_operation(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """生成操作定义"""
        operation = {
            "summary": endpoint.summary,
            "description": endpoint.description,
            "operationId": endpoint.operation_id,
            "tags": endpoint.tags,
        }

        # 参数
        if endpoint.parameters:
            operation["parameters"] = [
                self._generate_parameter(param) for param in endpoint.parameters
            ]

        # 请求体
        if endpoint.request_body:
            operation["requestBody"] = endpoint.request_body

        # 响应
        operation["responses"] = {}
        for response in endpoint.responses:
            operation["responses"][str(response.status_code)] = self._generate_response(response)

        # 安全
        if endpoint.security:
            operation["security"] = [{scheme: []} for scheme in endpoint.security]

        # 弃用
        if endpoint.deprecated:
            operation["deprecated"] = True

        return operation

    def _generate_parameter(self, param: APIParameter) -> Dict[str, Any]:
        """生成参数定义"""
        parameter = {
            "name": param.name,
            "in": param.location,
            "description": param.description,
            "required": param.required,
            "schema": self._generate_field_schema(APIField(
                name=param.name,
                type=param.type,
                example=param.example,
            )),
        }

        return parameter

    def _generate_response(self, response: APIResponse) -> Dict[str, Any]:
        """生成响应定义"""
        resp = {
            "description": response.description,
        }

        if response.schema_ref:
            resp["content"] = {
                response.content_type: {
                    "schema": {"$ref": f"#/components/schemas/{response.schema_ref}"}
                }
            }

        if response.example:
            resp["content"] = resp.get("content", {})
            resp["content"][response.content_type] = resp["content"].get(response.content_type, {})
            resp["content"][response.content_type]["example"] = response.example

        return resp

    def _generate_schemas(self) -> Dict[str, Any]:
        """生成Schema定义"""
        schemas = {}

        for schema in self.api_doc.schemas:
            # 基础Schema
            schemas[schema.name] = self._generate_schema_definition(schema)

            # Create Schema（不包含id和自动生成的字段）
            create_fields = [f for f in schema.fields if f.name not in ['id', 'created_at', 'updated_at']]
            create_schema = APISchema(
                name=f"{schema.name}Create",
                description=f"创建{schema.name}请求",
                fields=create_fields,
                required_fields=[f.name for f in create_fields if f.required],
            )
            schemas[create_schema.name] = self._generate_schema_definition(create_schema)

            # Update Schema
            update_schema = APISchema(
                name=f"{schema.name}Update",
                description=f"更新{schema.name}请求",
                fields=create_fields,
                required_fields=[f.name for f in create_fields if f.required],
            )
            schemas[update_schema.name] = self._generate_schema_definition(update_schema)

            # Partial Update Schema
            partial_schema = APISchema(
                name=f"{schema.name}PartialUpdate",
                description=f"部分更新{schema.name}请求",
                fields=[APIField(
                    name=f.name,
                    type=f.type,
                    description=f.description,
                    required=False,
                    nullable=True,
                    **{k: v for k, v in f.__dict__.items() if k not in ['name', 'type', 'description', 'required', 'nullable']}
                ) for f in create_fields],
                required_fields=[],
            )
            schemas[partial_schema.name] = self._generate_schema_definition(partial_schema)

            # List Response Schema
            list_response = {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"$ref": f"#/components/schemas/{schema.name}"}
                    },
                    "total": {"type": "integer", "description": "总记录数"},
                    "page": {"type": "integer", "description": "当前页码"},
                    "page_size": {"type": "integer", "description": "每页数量"},
                    "pages": {"type": "integer", "description": "总页数"},
                },
                "required": ["items", "total", "page", "page_size"],
            }
            schemas[f"{schema.name}ListResponse"] = list_response

        # 添加通用响应Schema
        schemas["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "错误代码"},
                "message": {"type": "string", "description": "错误消息"},
                "details": {"type": "object", "description": "错误详情"},
            },
            "required": ["code", "message"],
        }

        schemas["ValidationError"] = {
            "type": "object",
            "properties": {
                "field": {"type": "string", "description": "字段名"},
                "message": {"type": "string", "description": "验证错误消息"},
                "value": {"description": "字段值"},
            },
            "required": ["field", "message"],
        }

        return schemas

    def _generate_schema_definition(self, schema: APISchema) -> Dict[str, Any]:
        """生成单个Schema定义"""
        properties = {}
        for field in schema.fields:
            properties[field.name] = self._generate_field_schema(field)

        return {
            "type": "object",
            "description": schema.description,
            "properties": properties,
            "required": schema.required_fields,
        }

    def _generate_field_schema(self, field: APIField) -> Dict[str, Any]:
        """生成字段Schema"""
        schema = {}

        # 引用其他Schema
        if field.ref:
            return {"$ref": f"#/components/schemas/{field.ref}"}

        # 数组类型
        if field.type == DataType.ARRAY:
            schema["type"] = "array"
            schema["items"] = {"type": "string"}  # 默认字符串数组
        # 对象类型
        elif field.type == DataType.OBJECT:
            schema["type"] = "object"
        # 基本类型
        else:
            type_mapping = {
                DataType.STRING: "string",
                DataType.INTEGER: "integer",
                DataType.NUMBER: "number",
                DataType.BOOLEAN: "boolean",
                DataType.DATE: "string",
                DataType.DATETIME: "string",
                DataType.EMAIL: "string",
                DataType.UUID: "string",
            }
            schema["type"] = type_mapping.get(field.type, "string")

            # 格式
            format_mapping = {
                DataType.DATE: "date",
                DataType.DATETIME: "date-time",
                DataType.EMAIL: "email",
                DataType.UUID: "uuid",
            }
            if field.type in format_mapping:
                schema["format"] = format_mapping[field.type]

        # 描述
        if field.description:
            schema["description"] = field.description

        # 示例
        if field.example is not None:
            schema["example"] = field.example

        # 枚举
        if field.enum:
            schema["enum"] = field.enum

        # 长度限制
        if field.min_length is not None:
            schema["minLength"] = field.min_length
        if field.max_length is not None:
            schema["maxLength"] = field.max_length

        # 数值范围
        if field.minimum is not None:
            schema["minimum"] = field.minimum
        if field.maximum is not None:
            schema["maximum"] = field.maximum

        # 模式
        if field.pattern:
            schema["pattern"] = field.pattern

        # 可空
        if field.nullable:
            schema["nullable"] = True

        # 默认值
        if field.default is not None:
            schema["default"] = field.default

        return schema

    def _generate_common_responses(self) -> Dict[str, Any]:
        """生成通用响应定义"""
        return {
            "BadRequest": {
                "description": "请求参数错误",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "Unauthorized": {
                "description": "未授权",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "NotFound": {
                "description": "资源不存在",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "Conflict": {
                "description": "资源冲突",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
        }


class CRUDGenerator:
    """CRUD代码生成器"""

    def __init__(self, api_doc: APIDocument):
        self.api_doc = api_doc

    def generate(self) -> Dict[str, str]:
        """生成CRUD代码"""
        files = {}

        for schema in self.api_doc.schemas:
            # 生成模型代码
            files[f"models/{self._to_snake_case(schema.name)}.py"] = self._generate_model(schema)

            # 生成服务代码
            files[f"services/{self._to_snake_case(schema.name)}_service.py"] = self._generate_service(schema)

            # 生成路由代码
            files[f"api/v1/{self._to_snake_case(schema.name)}s.py"] = self._generate_router(schema)

            # 生成Schema代码
            files[f"schemas/{self._to_snake_case(schema.name)}.py"] = self._generate_schemas_py(schema)

        return files

    def _generate_model(self, schema: APISchema) -> str:
        """生成SQLAlchemy模型"""
        fields_code = []
        for field in schema.fields:
            if field.name in ['id', 'created_at', 'updated_at']:
                continue

            field_type = self._get_sqlalchemy_type(field)
            constraints = []

            if field.required and not field.nullable:
                constraints.append("nullable=False")
            else:
                constraints.append("nullable=True")

            if field.unique:
                constraints.append("unique=True")

            if field.index:
                constraints.append("index=True")

            if field.default is not None:
                constraints.append(f"default={repr(field.default)}")

            fields_code.append(f"    {field.name} = Column({field_type}, {', '.join(constraints)})")

        return f'''"""
{schema.name} Model
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class {schema.name}(Base):
    """{schema.description}"""
    __tablename__ = "{self._to_snake_case(schema.name)}s"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
{chr(10).join(fields_code)}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<{schema.name}(id={{self.id}})>"

    def to_dict(self):
        return {{
            "id": self.id,
{chr(10).join([f'            "{f.name}": self.{f.name},' for f in schema.fields if f.name not in ['created_at', 'updated_at']])}
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }}
'''

    def _generate_service(self, schema: APISchema) -> str:
        """生成服务层代码"""
        model_name = schema.name
        model_var = self._to_snake_case(model_name)

        return f'''"""
{model_name} Service
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from app.models.{model_var} import {model_name}
from app.schemas.{model_var} import {model_name}Create, {model_name}Update


class {model_name}Service:
    """{model_name}业务逻辑服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        sort: Optional[str] = None,
        search: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """获取分页列表"""
        query = self.db.query({model_name})

        # 应用筛选
        for key, value in filters.items():
            if value is not None and hasattr({model_name}, key):
                query = query.filter(getattr({model_name}, key) == value)

        # 搜索
        if search:
            # 根据实际需求实现搜索逻辑
            pass

        # 排序
        if sort:
            if sort.startswith('-'):
                query = query.order_by(desc(sort[1:]))
            else:
                query = query.order_by(asc(sort))
        else:
            query = query.order_by(desc({model_name}.created_at))

        # 分页
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return {{
            "items": [item.to_dict() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }}

    def get_by_id(self, id: str) -> Optional[{model_name}]:
        """根据ID获取详情"""
        return self.db.query({model_name}).filter({model_name}.id == id).first()

    def create(self, data: {model_name}Create) -> {model_name}:
        """创建记录"""
        db_item = {model_name}(**data.dict())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def update(self, id: str, data: {model_name}Update) -> Optional[{model_name}]:
        """更新记录"""
        db_item = self.get_by_id(id)
        if not db_item:
            return None

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)

        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def delete(self, id: str) -> bool:
        """删除记录"""
        db_item = self.get_by_id(id)
        if not db_item:
            return False

        self.db.delete(db_item)
        self.db.commit()
        return True


# 服务实例工厂
def get_{model_var}_service(db: Session) -> {model_name}Service:
    return {model_name}Service(db)
'''

    def _generate_router(self, schema: APISchema) -> str:
        """生成FastAPI路由"""
        model_name = schema.name
        model_var = self._to_snake_case(model_name)
        path = self._to_kebab_case(model_name)

        return f'''"""
{model_name} API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.{model_var}_service import get_{model_var}_service, {model_name}Service
from app.schemas.{model_var} import (
    {model_name} as {model_name}Schema,
    {model_name}Create,
    {model_name}Update,
    {model_name}PartialUpdate,
    {model_name}ListResponse,
)

router = APIRouter(prefix="/{path}s", tags=["{model_name}"])


@router.get("/", response_model={model_name}ListResponse)
async def list_{model_var}s(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort: Optional[str] = Query(None, description="排序字段"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """获取{model_name}列表"""
    return service.get_list(page=page, page_size=page_size, sort=sort, search=search)


@router.post("/", response_model={model_name}Schema, status_code=status.HTTP_201_CREATED)
async def create_{model_var}(
    data: {model_name}Create,
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """创建{model_name}"""
    return service.create(data)


@router.get("/{{id}}", response_model={model_name}Schema)
async def get_{model_var}(
    id: str,
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """获取{model_name}详情"""
    item = service.get_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return item


@router.put("/{{id}}", response_model={model_name}Schema)
async def update_{model_var}(
    id: str,
    data: {model_name}Update,
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """更新{model_name}"""
    item = service.update(id, data)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return item


@router.patch("/{{id}}", response_model={model_name}Schema)
async def partial_update_{model_var}(
    id: str,
    data: {model_name}PartialUpdate,
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """部分更新{model_name}"""
    item = service.update(id, data)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return item


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{model_var}(
    id: str,
    current_user: User = Depends(get_current_active_user),
    service: {model_name}Service = Depends(get_{model_var}_service),
):
    """删除{model_name}"""
    success = service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return None
'''

    def _generate_schemas_py(self, schema: APISchema) -> str:
        """生成Pydantic Schema"""
        model_name = schema.name

        # 基础字段
        base_fields = []
        for field in schema.fields:
            if field.name in ['id', 'created_at', 'updated_at']:
                continue

            type_str = self._get_pydantic_type(field)
            default = "..." if field.required else f"{repr(field.default) if field.default is not None else 'None'}"

            field_def = f"    {field.name}: {type_str} = Field({default}, description=\"{field.description}\")"
            base_fields.append(field_def)

        return f'''"""
{model_name} Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class {model_name}Base(BaseModel):
    """{model_name}基础Schema"""
{chr(10).join(base_fields) if base_fields else "    pass"}


class {model_name}Create({model_name}Base):
    """创建{model_name}请求"""
    pass


class {model_name}Update({model_name}Base):
    """更新{model_name}请求"""
    pass


class {model_name}PartialUpdate(BaseModel):
    """部分更新{model_name}请求"""
{chr(10).join([f.replace(' = ...', ' = None') for f in base_fields]) if base_fields else "    pass"}


class {model_name}({model_name}Base):
    """{model_name}响应Schema"""
    id: str = Field(..., description="唯一标识")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class {model_name}ListResponse(BaseModel):
    """{model_name}列表响应"""
    items: List[{model_name}] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")
'''

    def _get_sqlalchemy_type(self, field: APIField) -> str:
        """获取SQLAlchemy类型"""
        type_mapping = {
            DataType.STRING: "String(255)",
            DataType.INTEGER: "Integer",
            DataType.NUMBER: "Float",
            DataType.BOOLEAN: "Boolean",
            DataType.DATE: "Date",
            DataType.DATETIME: "DateTime(timezone=True)",
            DataType.EMAIL: "String(255)",
            DataType.UUID: "String(36)",
            DataType.TEXT: "Text",
            DataType.JSON: "JSON",
        }

        # 根据约束调整类型
        if field.type == DataType.STRING and field.max_length:
            return f"String({field.max_length})"

        return type_mapping.get(field.type, "String(255)")

    def _get_pydantic_type(self, field: APIField) -> str:
        """获取Pydantic类型"""
        type_mapping = {
            DataType.STRING: "str",
            DataType.INTEGER: "int",
            DataType.NUMBER: "float",
            DataType.BOOLEAN: "bool",
            DataType.DATE: "date",
            DataType.DATETIME: "datetime",
            DataType.EMAIL: "str",
            DataType.UUID: "str",
        }

        base_type = type_mapping.get(field.type, "str")

        if not field.required:
            return f"Optional[{base_type}]"

        return base_type

    def _to_snake_case(self, name: str) -> str:
        """转换为snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _to_kebab_case(self, name: str) -> str:
        """转换为kebab-case"""
        return self._to_snake_case(name).replace('_', '-')


# API接口函数
def generate_api_from_prd(prd_content: str) -> Dict[str, Any]:
    """
    从PRD生成API规范

    Args:
        prd_content: PRD文档内容

    Returns:
        包含OpenAPI规范和CRUD代码的字典
    """
    # 提取API文档
    extractor = PRDDataExtractor(prd_content)
    api_doc = extractor.extract()

    # 生成OpenAPI规范
    openapi_gen = OpenAPIGenerator(api_doc)
    openapi_spec = openapi_gen.generate()

    # 生成CRUD代码
    crud_gen = CRUDGenerator(api_doc)
    crud_files = crud_gen.generate()

    return {
        "openapi": openapi_spec,
        "crud_files": crud_files,
        "metadata": {
            "title": api_doc.title,
            "version": api_doc.version,
            "schema_count": len(api_doc.schemas),
            "endpoint_count": len(api_doc.endpoints),
            "schemas": [s.name for s in api_doc.schemas],
        }
    }


def generate_swagger_ui(openapi_spec: Dict[str, Any]) -> str:
    """
    生成Swagger UI HTML

    Args:
        openapi_spec: OpenAPI规范

    Returns:
        Swagger UI HTML字符串
    """
    spec_json = json.dumps(openapi_spec, ensure_ascii=False, indent=2)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{openapi_spec.get('info', {}).get('title', 'API Documentation')}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin: 0; background: #fafafa; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({{
                spec: {spec_json},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
            }});
        }};
    </script>
</body>
</html>'''
