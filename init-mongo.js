db = db.getSiblingDB('flyertalk')

console.log("Creating intitial 'flyertalk' db")

db.createUser({
  user: process.env.MONGO_SCRAPY_USER,
  pwd: process.env.MONGO_SCRAPY_PWD,
  roles: [{ role: 'readWrite', db: 'flyertalk' }]
});