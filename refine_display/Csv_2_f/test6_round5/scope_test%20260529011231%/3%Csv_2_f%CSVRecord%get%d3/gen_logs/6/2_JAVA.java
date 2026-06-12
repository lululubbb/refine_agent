package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_6Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        mapping.put("header3", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1);
    }

    @Test
    public void testGet_normalCase() throws Exception {
        String result = csvRecord.get("header1");
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_nonExistentHeader() throws Exception {
        String result = csvRecord.get("header4");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_headerMappingNull() throws Exception {
        CSVRecord recordWithNullMapping = new CSVRecord(new String[]{"value1"}, null, null, 1);
        Exception exception = Assertions.assertThrows(IllegalStateException.class, () -> {
            recordWithNullMapping.get("header1");
        });
        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getMessage());
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        Map<String, Integer> invalidMapping = new HashMap<>();
        invalidMapping.put("header1", 3); // Invalid index
        CSVRecord recordWithInvalidIndex = new CSVRecord(new String[]{"value1", "value2"}, invalidMapping, null, 1);
        Exception exception = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            recordWithInvalidIndex.get("header1");
        });
        Assertions.assertEquals("Index for header 'header1' is 3 but CSVRecord only has 2 values!", exception.getMessage());
    }
}