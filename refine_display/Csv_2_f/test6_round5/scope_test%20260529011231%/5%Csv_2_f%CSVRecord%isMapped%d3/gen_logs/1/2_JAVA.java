package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_5_1Test {

    @Test
    public void testisMapped_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertTrue(record.isMapped("name"));
    }

    @Test
    public void testisMapped_keyNotPresent() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertFalse(record.isMapped("otherName"));
    }

    @Test
    public void testisMapped_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        
        Assertions.assertFalse(record.isMapped("name"));
    }

    @Test
    public void testisMapped_nullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        
        Assertions.assertFalse(record.isMapped("name"));
    }
}