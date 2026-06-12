package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_2Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        mapping.put("name", 0);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertTrue(csvRecord.isSet("name"));
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        mapping.put("name", 2);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("name"));
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("name"));
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("nonExistentName"));
    }

    @Test
    public void testisSet_nullName() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet(null));
    }
}