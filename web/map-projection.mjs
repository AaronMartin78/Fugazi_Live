// Uniform Mercator scale preserves local shapes in regional views.
// Keep the original equirectangular world overview.
const radians = degrees => degrees * Math.PI / 180;
const mercatorY = latitude => Math.log(Math.tan(Math.PI / 4 + radians(Math.max(-85,Math.min(85,latitude))) / 2));

export function mapProjection(bounds, regional, width = 960, height = 460) {
  const [west,east,south,north] = bounds;
  if (!regional) return ([lon,lat]) => [(lon-west)/(east-west)*width,(north-lat)/(north-south)*height];
  const minX = radians(west), maxX = radians(east), minY = mercatorY(south), maxY = mercatorY(north);
  const scale = Math.min((width-32)/(maxX-minX),(height-32)/(maxY-minY));
  const centerX = (minX+maxX)/2, centerY = (minY+maxY)/2;
  return ([lon,lat]) => [width/2+(radians(lon)-centerX)*scale,height/2+(centerY-mercatorY(lat))*scale];
}
