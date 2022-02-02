/*
version 2022.02.02.1
*/

function isNull(v) {
    if (v===null || v === 'null') return true;
    else return false;
}

function stringify(v) {
    var res = [];
    for (var i=0; i<v.length; i++) {
        res.push(JSON.stringify(v[i]));
    }
    return res;
}

// Edit these before use
const ENDPOINT = ""
const PROJECT_ID = ""
const COLLECTION_ID = ""

Vue.createApp({
    data() {
        return {
            email: '',
            password: '',
            loggedin: false,
            session_id: null,
            save_session: true,
            documents: [],
        }
    },
    mounted() {
        const sdk = new Appwrite();
        sdk
            .setEndpoint(ENDPOINT)
            .setProject(PROJECT_ID);
        this.sdk = sdk;
        if (isNull(localStorage.getItem('appwrite_save_session'))) this.save_session = true;
        else this.save_session = localStorage.getItem('appwrite_save_session');
        this.session_id = localStorage.getItem('appwrite_session_id');
        this.getSession();
    },
    watch: {
        loggedin() {
            if (this.loggedin) {
                Swal.fire('Success', 'logged in, session_id='+this.session_id, 'success');
                this.refreshDocuments();
            }
            else Swal.fire('Success', 'logged out', 'success');
        },
        session_id() {
            if (this.save_session) this.saveSession();
        },
        save_session() {
            localStorage.setItem('appwrite_save_session', this.save_session);
            if (!this.save_session) {
                localStorage.removeItem('appwrite_session_id');
            }
        }
    },
    methods: {
        createSession() {
            var app = this;
            let promise = app.sdk.account.createSession(app.email, app.password);
            promise.then(function (response) {
                app.session_id = response.$id;
                app.loggedin = true;
            }, function (error) {
                Swal.fire('Login failed: email or password invalid.', error, 'error');
                console.log(error); // Failure
            });
        },
        deleteSession() {
            var app = this;
            app.documents = [];
            let promise = app.sdk.account.deleteSession(app.session_id);
            promise.then(function (response) {
                app.session_id = null;
                app.loggedin = false;
            }, function (error) {
                Swal.fire('Unknown Appwrite Error', error, 'error');
                console.log(error); // Failure
            });
        },
        saveSession() {
            if (!isNull(this.session_id)) localStorage.setItem('appwrite_session_id', this.session_id);
            else localStorage.removeItem('appwrite_session_id')
        },
        getSession() {
            var app = this;
            if (!isNull(app.session_id)) {
                console.log('Trying to log in with saved session_id');
                let promise = app.sdk.account.getSession(app.session_id);
                promise.then(function (response) {
                    app.loggedin = true;
                }, function (error) {
                    console.log(error); // Failure
                    Swal.fire('Login failed: session expired.', error, 'error');
                    app.session_id = null;
                    app.loggedin = false;
                });
            }
            else {
                console.log('Not trying to log in session since session_id is null');
            }
        },
        refreshDocuments() {
            var app = this;
            app.documents = [];
            let promise = app.sdk.database.listDocuments(COLLECTION_ID);
            promise.then(function (response) {
                console.log(response);
                for (var i=0; i<response.sum; i++) {
                    var doc = response.documents[i];
                    var progs = [];
                    for (var j=0; j<doc.progs.length; j++) {
                        var prog = JSON.parse(doc.progs[j])
                        progs.push({
                            "name": prog.name,
                            "hold": prog.hold,
                            "version": prog.version
                        });
                    }
                    app.documents.push({
                        "id": doc.$id,
                        "name": doc.name,
                        "date": doc.date,
                        "status": doc.status,
                        "progs": progs,
                        "msg": doc.msg
                    });
                }
            }, function (error) {
                Swal.fire('Unknown Appwrite Error', error, 'error');
                console.log(error); // Failure
            });
        },
        saveDocument() {
            var app = this;
            var error_occured = false;
            for(var i=0; i<app.documents.length; i++) {
                var doc = app.documents[i];
                var id = doc.id;
                var document = {
                    "status": doc.status,
                    "progs": stringify(doc.progs)
                };
                //delete document.id;
                let promise = app.sdk.database.updateDocument(COLLECTION_ID, id, document);
                promise.then(function (response) {
                    console.log(response); // Success
                }, function (error) {
                    error_occured = true;
                    Swal.fire('Unknown Appwrite Error', error, 'error');
                    console.log(error); // Failure
                });
            }
            if (!error_occured) Swal.fire('Success', 'Document saved to appwrite', 'success');
        }
    }
}).mount('#app');