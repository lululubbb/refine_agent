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
        
        Assertions.assertTrue(csvRecord.isSet("name"), "Expected 'name' to be set when mapped and within bounds.");
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        mapping.put("name", 2);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("name"), "Expected 'name' to not be set when mapped but out of bounds.");
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("name"), "Expected 'name' to not be set when not mapped.");
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet("nonExistentName"), "Expected 'nonExistentName' to not be set with empty mapping.");
    }

    @Test
    public void testisSet_nullName() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertFalse(csvRecord.isSet(null), "Expected null name to not be set.");
    }
}