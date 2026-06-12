package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
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
    public void testGet_validHeaderWithDifferentValues() throws Exception {
        String[] newValues = {"newValue1", "newValue2", "newValue3"};
        Map<String, Integer> newMapping = new HashMap<>();
        newMapping.put("header1", 0);
        newMapping.put("header2", 1);
        newMapping.put("header3", 2);
        CSVRecord recordWithDifferentValues = new CSVRecord(newValues, newMapping, null, 2);
        String result = recordWithDifferentValues.get("header2");
        Assertions.assertEquals("newValue2", result);
    }
}