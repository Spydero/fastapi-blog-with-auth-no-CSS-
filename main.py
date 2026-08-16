from typing import Optional
## meow meow meow meow meow meow meow meow meow.MEOWMEOWMEOW
from fastapi import FastAPI, Request, Depends, Form, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import IntegrityError

from database import engine, Base, get_db, SessionLocal
import models 
from auth import hash_password, verify_password, create_session_token

app = FastAPI()


Base.metadata.create_all(bind=engine)

def seed_categories():
  db = SessionLocal()
  try:
    if db.query(models.Category).count() == 0:
      for name in ["Technology", "Life", "Travel", "Food"]:
        db.add(models.Category(name=name))
      db.commit()
  finally:
    db.close()
    
seed_categories()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


def get_current_user(
  session_token: Optional[str] = Cookie(default=None),
  db: DBSession = Depends(get_db)
) -> Optional[models.User]:
  """
  Reusable dependency -> figures out who ( if anyone ) is logged in,
  based on the 'session_token' cookie. Returns None if not logged in,
  or if the cookie doesn't match a real session (expired or tampered etc)
  """
  if session_token is None:
    return None
  
  db_session = db.get(models.Session, session_token)
  
  if db_session is None:
    return None 
  
  return db_session.user


@app.get("/", response_class=HTMLResponse)
def home(
  request: Request, 
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db),
  ):
  posts = db.query(models.Post).order_by(models.Post.created_at.desc()).all()
  return templates.TemplateResponse(
    request=request, 
    name="index.html", 
    context={"page_title": "My Blog", 
             "username": current_user.username if current_user 
             else "Guest", 
             "current_user": current_user,
             "posts": posts
             })


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request,
                  current_user: Optional[models.User] = Depends(get_current_user)
                  ):
  """Just displays empty registration form"""
  if current_user:
    return RedirectResponse(url="/", status_code=303)
  
  return templates.TemplateResponse(
    request=request, name="register.html", context={"page_title": "Register"}
  )
  


@app.post("/register")
def register_submit(
  request: Request,
  username: str = Form(...),
  password: str = Form(...),
  db: DBSession = Depends(get_db),
):
  """Handles form submission: hash the password, save the user"""
  new_user = models.User(
    username=username,
    hashed_password=hash_password(password)
  )
  db.add(new_user)
  
  try:
    db.commit()
  except IntegrityError:
    # This fires if `username`` already exists (our unique=True constraint)
    db.rollback()
    return templates.TemplateResponse(
      request=request,
      name="register.html",
      context={
        "page_title": "Register",
        "error": "The username is already taken"
      },
    )
    
  # PRG Pattern: redirect after a successful POST, so refreshing the 
  # result page doesn't accidentally submit the form.
  return RedirectResponse(url="/", status_code=303)
  
  

@app.get("/login", response_class=HTMLResponse)
def login_form(
  request: Request,
  current_user: Optional[models.User] = Depends(get_current_user),
):
  if current_user:
    return RedirectResponse("/", status_code=303)
  return templates.TemplateResponse(
    request=request, name="login.html", context={"page_title": "Log in"}
  )
  

@app.post("/login")
def login_submit(
  request: Request,
  username: str = Form(...),
  password: str = Form(...),
  db: DBSession = Depends(get_db),
):
  user = db.query(models.User).filter(models.User.username == username).first()
  
  # Deliberately vague error -> doesn't reveal whether username exists or password was wrong
  # which is the standard practice
  # (avoids leaking which usernames are registered)
  invalid_creds_error = templates.TemplateResponse(
    request=request,
    name="login.html",
    context={"page_title": "Log in", "error": "Invalid username or password."},
  )
  
  if user is None:
    return invalid_creds_error
  if not verify_password(password, user.hashed_password):
    return invalid_creds_error
  
  token = create_session_token()
  db.add(models.Session(id=token, user_id=user.id))
  db.commit()
  
  redirect = RedirectResponse(url="/", status_code=303)
  redirect.set_cookie(
    key="session_token",
    value=token,
    httponly=True, #Javascript can't read this cookie -> blocks a common attack (XSS cookie theft)
    samesite="lax", # blocks cookie being sent on most cross-site requests -> CSRF mitigation
    max_age=60 * 60 * 24 * 7, # 7 days
  )
  return redirect 


@app.post("/logout")
def logout(
  session_token: Optional[str] = Cookie(default=None),
  db: DBSession = Depends(get_db)
):
  if session_token:
    db_session = db.get(models.Session, session_token)
    if db_session:
      db.delete(db_session)
      db.commit()
      
  redirect = RedirectResponse(url="/", status_code=303)
  redirect.delete_cookie("session_token")
  return redirect


@app.get("/posts/new", response_class=HTMLResponse)
def new_post_form(
  request: Request,
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db)
):
  if current_user is None:
    return RedirectResponse(url="/login", status_code=303)
  
  categories = db.query(models.Category).all()
  return templates.TemplateResponse(
    request=request,
    name="new_post.html",
    context={"page_title": "New post", "current_user": current_user, "categories": categories}
  )


@app.post("/posts/new")
def new_post_submit(
  title: str = Form(...),
  content: str = Form(...),
  category_id: int = Form(...),
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db)
):
  if current_user is None:
    return RedirectResponse(url="/login", status_code=303)
  
  new_post = models.Post(
    title=title,
    content=content,
    category_id=category_id,
    author_id=current_user.id,
  )
  
  db.add(new_post)
  db.commit()
  db.refresh(new_post) # so new_post.id is populated with real auto generated id
  return RedirectResponse(url=f"/posts/{new_post.id}", status_code=303)


@app.get("/posts/{post_id}", response_class=HTMLResponse)
def view_post(
  post_id: int,
  request: Request,
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db),
):
  post = db.get(models.Post, post_id)
  if post is None:
    raise HTTPException(status_code=404, detail="Post not found")
  
  return templates.TemplateResponse(
    request=request,
    name="post_detail.html",
    context={"page_title": post.title, "current_user": current_user, "post": post}
  )


def can_modify(user: Optional[models.User], post: models.Post) -> bool:
  """True if this user is allowed to edit/delete this post""" ###########
  if user is None:
    return False 
  
  return user.id == post.author_id or user.role == "admin"


  
@app.get("/posts/{post_id}/edit", response_class=HTMLResponse)
def edit_post_form(
  post_id: int,
  request: Request,
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db),
):
  post = db.get(models.Post, post_id)
  if post is None:
    raise HTTPException(status_code=404, detail="Post not found")
  if not can_modify(current_user, post):
    raise HTTPException(status_code=403, detail="Not allowed to edit this post")
  
  
  categories = db.query(models.Category).all()
  return templates.TemplateResponse(
    request=request,
    name="edit_post.html",
    context={"page_title": "Edit post", "post": post, "categories": categories},
  )
  
  

@app.post("/posts/{post_id}/edit")
def edit_post_submit(
  post_id: int,
  title: str = Form(...),
  content: str = Form(...),
  category_id: int = Form(...),
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db)
):
  post = db.get(models.Post, post_id)
  if post is None:
    raise HTTPException(status_code=404, detail="Post not found")
  if not can_modify(current_user, post):
    raise HTTPException(status_code=403, detail="Not allowed to edit this post")
  
  post.title = title
  post.content = content 
  post.category_id = category_id
  db.commit()
  return RedirectResponse(url=f"/posts/{post.id}", status_code=303)
  


@app.post("/posts/{post_id}/delete")
def delete_post(
  post_id: int,
  current_user: Optional[models.User] = Depends(get_current_user),
  db: DBSession = Depends(get_db),
):
  post = db.get(models.Post, post_id)
  if post is None:
    return HTTPException(status_code=404, detail="Post not found")
  if not can_modify(current_user, post):
    raise HTTPException(status_code=403, detail="Not allowed to delete this post")

  db.delete(post)
  db.commit()
  return RedirectResponse(url="/", status_code=303)



@app.post("/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    content: str = Form(...),
    current_user: Optional[models.User] = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    post = db.get(models.Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    db.add(models.Comment(content=content, post_id=post_id, author_id=current_user.id))
    db.commit()
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)
  
  
