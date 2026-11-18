// Groups use archive country labels, not geocoded city coverage or map bounds.
export const regionGroups = {
  'north-america': {name:'North America', countries:['USA','Canada']},
  'south-america': {name:'South America', countries:['Argentina','Brazil','Chile']},
  europe: {name:'Europe', countries:['Austria','Belgium','Czech Republic','Czechoslovakia','Denmark','England','Finland','France','Germany','Hungary','Iceland','Ireland','Italy','Netherlands','Northern Ireland','Norway','Poland','Portugal','Scotland','Slovenia','Spain','Spain/Basque','Sweden','Switzerland','Wales','Yugoslavia']},
  asia: {name:'Asia', countries:['Hong Kong','Japan','Malaysia','Singapore']},
  oceania: {name:'Oceania', countries:['Australia','New Zealand']},
};
export function inRegion(show, region = '') {
  return !region || !!regionGroups[region]?.countries.includes(show.location_as_listed.country);
}
