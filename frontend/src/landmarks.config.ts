// Известные достопримечательности Дубая с фото (Wikimedia/Wikipedia).
// Фото-пины показываются вместе с оверлеем «Достопримечательности».
// ВНИМАНИЕ: часть изображений с en.wikipedia (fair-use) — для публикации
// нужна атрибуция/замена на свободные (Wikimedia Commons).
export interface Landmark {
  name: string;
  lng: number;
  lat: number;
  photo: string;
}

export const LANDMARKS: Landmark[] = [
  {
    name: "Burj Khalifa",
    lng: 55.2744,
    lat: 25.1972,
    photo:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Burj_Khalifa_%28worlds_tallest_building%29_and_the_Dubai_skyline_%2825781049892%29.jpg/330px-Burj_Khalifa_%28worlds_tallest_building%29_and_the_Dubai_skyline_%2825781049892%29.jpg",
  },
  {
    name: "Burj Al Arab",
    lng: 55.1853,
    lat: 25.1412,
    photo:
      "https://upload.wikimedia.org/wikipedia/en/thumb/2/2a/Burj_Al_Arab%2C_Dubai%2C_by_Joi_Ito_Dec2007.jpg/330px-Burj_Al_Arab%2C_Dubai%2C_by_Joi_Ito_Dec2007.jpg",
  },
  {
    name: "Atlantis, The Palm",
    lng: 55.1173,
    lat: 25.1304,
    photo:
      "https://upload.wikimedia.org/wikipedia/en/thumb/f/f3/Hotel_Atlantis_at_Sunset%2C_The_Palm_-_Dubai_%2849510861268%29.jpg/330px-Hotel_Atlantis_at_Sunset%2C_The_Palm_-_Dubai_%2849510861268%29.jpg",
  },
  {
    name: "The Dubai Mall",
    lng: 55.2796,
    lat: 25.1985,
    photo:
      "https://upload.wikimedia.org/wikipedia/en/thumb/d/df/Dubai_Mall_10.jpg/330px-Dubai_Mall_10.jpg",
  },
  {
    name: "Museum of the Future",
    lng: 55.282,
    lat: 25.2195,
    photo:
      "https://upload.wikimedia.org/wikipedia/en/thumb/8/8c/Museum_of_the_future%2C_Dubai.jpeg/330px-Museum_of_the_future%2C_Dubai.jpeg",
  },
  {
    name: "Ain Dubai",
    lng: 55.1189,
    lat: 25.079,
    photo:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/2022_Ain_Dubai_6_%2851824167326%29.jpg/330px-2022_Ain_Dubai_6_%2851824167326%29.jpg",
  },
  {
    name: "Jumeirah Mosque",
    lng: 55.241,
    lat: 25.2333,
    photo:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Jumeira_Mosque_Dubai.jpg/330px-Jumeira_Mosque_Dubai.jpg",
  },
];
