from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database.connection import get_db
from app.models.user import User, UserType
from app.auth.auth import authenticate_user, create_access_token, get_password_hash
from app.auth.profile import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    user_type: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user.user_type.lower() not in ["tenant", "client"]:
        raise HTTPException(status_code=400, detail="User type must be 'tenant' or 'client'")
    
    hashed_password = get_password_hash(user.password)
    user_type_enum = UserType.TENANT if user.user_type.lower() == "tenant" else UserType.CLIENT
    
    db_user = User(
        email=user.email, 
        name=user.name, 
        user_type=user_type_enum,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return {"message": "User created successfully", "unique_id": db_user.unique_id}

@router.post("/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    authenticated_user = await authenticate_user(db, user.email, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": authenticated_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "unique_id": current_user.unique_id,
        "name": current_user.name,
        "email": current_user.email,
        "user_type": current_user.user_type.value
    }