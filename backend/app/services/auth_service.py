"""
认证服务
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from loguru import logger

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, UserResponse, TokenResponse


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """验证用户"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_user(self, db: Session, user_create: UserCreate, is_superuser: bool = False) -> User:
        """创建用户"""
        try:
            # 检查用户名和邮箱是否已存在
            existing_user = db.query(User).filter(
                (User.username == user_create.username) | 
                (User.email == user_create.email)
            ).first()
            
            if existing_user:
                if existing_user.username == user_create.username:
                    raise ValueError("用户名已存在")
                if existing_user.email == user_create.email:
                    raise ValueError("邮箱已存在")
            
            # 创建新用户
            hashed_password = self.get_password_hash(user_create.password)
            db_user = User(
                username=user_create.username,
                email=user_create.email,
                full_name=user_create.full_name,
                avatar_url=user_create.avatar_url,
                bio=user_create.bio,
                phone=user_create.phone,
                department=user_create.department,
                position=user_create.position,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=False,  # 可以后续添加邮箱验证
                is_superuser=is_superuser
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            logger.info(f"用户创建成功: {db_user.username} ({db_user.email})")
            return db_user
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"用户创建失败 - 数据库完整性错误: {str(e)}")
            raise ValueError("用户名或邮箱已存在")
        except Exception as e:
            db.rollback()
            logger.error(f"用户创建失败: {str(e)}")
            raise
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        try:
            # 将字符串ID转换为整数
            user_id_int = int(user_id)
            return db.query(User).filter(User.id == user_id_int).first()
        except ValueError:
            logger.error(f"无效的用户ID格式: {user_id}")
            return None
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    def update_user_password(self, db: Session, user: User, new_password: str) -> User:
        """更新用户密码"""
        try:
            user.hashed_password = self.get_password_hash(new_password)
            db.commit()
            db.refresh(user)
            
            logger.info(f"用户密码更新成功: {user.username}")
            return user
            
        except Exception as e:
            db.rollback()
            logger.error(f"用户密码更新失败: {str(e)}")
            raise
    
    def create_token_response(self, user: User) -> TokenResponse:
        """创建令牌响应"""
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )
        refresh_token = self.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            phone=user.phone,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=user_response
        )


# 创建全局认证服务实例
auth_service = AuthService()
