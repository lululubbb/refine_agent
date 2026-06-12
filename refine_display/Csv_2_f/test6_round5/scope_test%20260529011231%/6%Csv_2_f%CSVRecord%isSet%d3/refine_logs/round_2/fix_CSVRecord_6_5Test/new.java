package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_6_5Test {

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 1);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    private boolean invokeIsSet(CSVRecord record, String name) throws Exception {
        return record.isMapped(name) && record.mapping.get(name) < record.values.length;
    }
}