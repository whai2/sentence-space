"""Common Pydantic base models for MongoDB documents"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, values=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoBaseModel(BaseModel):
    """
    MongoDB 문서를 위한 공통 베이스 모델

    Attributes:
        id: MongoDB ObjectId (_id 필드)
        created_at: 생성 시간 (UTC)
        updated_at: 수정 시간 (UTC)
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """
        모델을 딕셔너리로 변환 (MongoDB 저장용)

        Args:
            exclude_none: None 값을 제외할지 여부

        Returns:
            Dict[str, Any]: 딕셔너리 형태의 문서
        """
        data = self.model_dump(by_alias=True, exclude_none=exclude_none)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        딕셔너리에서 모델 인스턴스 생성

        Args:
            data: MongoDB 문서 데이터

        Returns:
            MongoBaseModel: 모델 인스턴스
        """
        return cls(**data)
