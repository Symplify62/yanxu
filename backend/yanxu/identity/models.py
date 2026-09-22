from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class Login(StrictModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=256, repr=False)


class UserCreate(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    detail: str = Field(default="", max_length=200)
    departmentId: str | None = None
    active: bool = True
    username: str | None = Field(default=None, max_length=80)
    password: str | None = Field(default=None, min_length=6, max_length=256, repr=False)
    roleId: str | None = None

    @model_validator(mode="after")
    def account_fields(self):
        if any((self.username, self.password, self.roleId)) and not all((self.username, self.password, self.roleId)):
            raise ValueError("创建登录账号需同时提供账号、密码及角色")
        if not self.name.strip():
            raise ValueError("姓名不能为空")
        return self


class UserPatch(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    detail: str | None = Field(default=None, max_length=200)
    departmentId: str | None = None
    active: bool | None = None
    username: str | None = Field(default=None, min_length=3, max_length=80)
    password: str | None = Field(default=None, min_length=6, max_length=256, repr=False)
    roleId: str | None = None


class RoleCreate(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=200)
    permissions: list[str] = Field(default_factory=list, max_length=5)


class RolePatch(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    permissions: list[str] | None = Field(default=None, max_length=5)


class DepartmentCreate(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    parentId: str | None = None


class DepartmentPatch(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    parentId: str | None = None


class GuestCreate(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    detail: str = Field(default="", max_length=200)
