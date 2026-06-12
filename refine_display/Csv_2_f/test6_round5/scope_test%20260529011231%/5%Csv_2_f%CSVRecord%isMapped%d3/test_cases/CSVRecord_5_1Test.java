package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_1Test {

    @Test
    public void testisMapped_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(true, record.isMapped("name"));
    }

    @Test
    public void testisMapped_keyNotPresent() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(false, record.isMapped("otherName"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_nullKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(false, record.isMapped(null));
    }

    @Test
    public void testisMapped_emptyStringKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(false, record.isMapped(""));
    }

    @Test
    public void testisMapped_caseSensitivity() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("Name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertEquals(false, record.isMapped("name"));
    }

    @Test
    public void testisMapped_boundaryValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        mapping.put("name1", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        
        Assertions.assertEquals(true, record.isMapped("name"));
        Assertions.assertEquals(true, record.isMapped("name1"));
        Assertions.assertEquals(false, record.isMapped("name2"));
    }
}