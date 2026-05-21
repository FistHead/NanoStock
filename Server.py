from fastapi import FastAPI
service = FastAPI()

# тест
@service.get("/")
def read_root():
    return {"Hello": "World"}