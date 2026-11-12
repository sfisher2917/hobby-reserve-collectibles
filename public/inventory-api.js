export const API_ORIGIN='https://hobby-reserve-inventory-api.onrender.com';
export async function requestLive(path){
 if(!/^\/api\/(inventory|items\/\d{9,15})$/.test(path))throw new Error('Invalid inventory request');
 const response=await fetch(API_ORIGIN+path,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(90000)});
 const data=await response.json();
 if(!response.ok){const error=new Error('Live inventory unavailable');error.code=data.error;error.status=response.status;throw error}
 return data;
}
