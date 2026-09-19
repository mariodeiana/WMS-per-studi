import { TestBed } from '@angular/core/testing';
import { Attachments } from './attachments';

describe('Evidence upload',()=>{
  let component: Attachments;
  beforeEach(()=>{ component=TestBed.runInInjectionContext(()=>new Attachments()); });
  it('encodes a file with its description and document type',async()=>{
    component.files.set([{file:new File(['evidence'],'proof.txt',{type:'text/plain'}),description:'Descrizione',document_type:'VERIFICA'}]);
    const [payload]=await component.payload(); expect(atob(payload.content_base64)).toBe('evidence'); expect(payload.filename).toBe('proof.txt'); expect(payload.description).toBe('Descrizione'); expect(payload.document_type).toBe('VERIFICA');
  });
  it('rejects files exceeding 5 MB without dropping valid selections',()=>{
    const picker={files:[new File(['ok'],'small.txt'),new File([new Uint8Array(5*1024*1024+1)],'large.txt')],value:'selected'};
    component.add({target:picker} as unknown as Event); expect(component.files().length).toBe(1); expect(component.error()).toContain('large.txt'); expect(picker.value).toBe('');
  });
});
